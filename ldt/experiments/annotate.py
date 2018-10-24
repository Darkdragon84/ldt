# -*- coding: utf-8 -*-
"""Annotating vector neighborhoods.

This module provides functionality for annotating vector neighborhoods
obtained from a number of word embeddings.

This is the second (and most important) step in LDT analysis default_workflow. The
input is pre-computed vector neighborhood files that are prepared with
:class:`~ldt.experiments.neighbors.VectorNeighborhoods` class. See the
documentation of that class for more details.

The output is saved in the experiments/neighbors_annotated/your_experiment_name
subfolder of the ldt resource folder specified in the configuration file.
These are tab-separated data files with columns indicating the presence of a
binary relation in target_neighbor word pairs (e.g. whether they are
synonyns), or a numerical indicator of a relationship (e.g. the distance
between them in an ontology). See the full list of available scores `here
<http://ldtoolkit.space/ldscores/>`_.

Todo:

    * parsing arguments from command line
    * ldt resource settings saved to metadata
    * add progressbars
    * multicore processing

"""

import os
import uuid
import pandas as pd
# import progressbar

from tqdm import tqdm
from multiprocessing import Pool
from joblib import Parallel, delayed
import dill
from pathos.multiprocessing import ProcessingPool
from vecto.utils.data import load_json

from ldt.experiments.metadata import Experiment
from ldt.load_config import config
from ldt.dicts.normalize import Normalization
from ldt.dicts.derivation.meta import DerivationAnalyzer
from ldt.dicts.semantics.metadictionary import MetaDictionary
from ldt.relations.pair import RelationsInPair

from ldt.load_config import config

class AnnotateVectorNeighborhoods(Experiment):
    """This class provides a simple interface for annotating pre-computed top_n
    vector neighborhoods for a given vocabulary sample.
    Vecto-style metadata is also generated."""

    #pylint: disable=too-many-arguments
    def __init__(self, experiment_name=config["experiments"]["experiment_name"],
                 extra_metadata=None,
                 overwrite=config["experiments"]["overwrite"], ld_scores="main",
                 output_dir=os.path.join(config["path_to_resources"],
                                         "experiments"),
                 ldt_analyzer=None, gdeps=False, cooccurrence=False):

        """ Annotating pre-computed top *n* neighbors for a given vocab sample

        Args:
            experiment_name (str): the human-readable name for the
                current experiment, which will be used to make a subfolder
                storing the generated data. If None, the folder will be simply
                timestamped.
            extra_metadata (dict): any extra fields to be added to the
                experiment metadata (overwriting any previously existing fields)
            output_dir (str): the *existing* path for saving the *subfolder*
                named with the specified experiment_name, where the output data
                and metadata.json file will be saved.
            overwrite (bool): if True, any previous data for the same
                experiment will be overwritten, and the experiment will be
                re-started.
            ldt_analyzer: :class:`~ldt.relations.pair.RelationsInPair`
                instance, with lexicographic, morphological and normalization
                resources set up as desired (see tutorial and
                class documentation). If None, default settings for English
                will be used.
            gdeps (bool): whether to use google dependency cooccurrence data
                (memory-intensive, off by default)
            cooccurrence (bool): whether to use corpus cooccurrence data
                (memory-intensive, off by default)
            ld_scores (str or list of str): "all" for all supported scores,
                or a list of ld_scores. Supported values are:

                    - "SharedPOS",
                    - "SharedMorphForm",
                    - "SharedDerivation",
                    - "NonCooccurring",
                    - "GDeps",
                    - "TargetFrequency",
                    - "NeighborFrequency",
                    - "Associations",
                    - "ShortestPath",
                    - "Synonyms",
                    - "Antonyms",
                    - "Meronyms",
                    - "Hyponyms",
                    - "Hypernyms",
                    - "OtherRelations",
                    - "Numbers",
                    - "ProperNouns",
                    - "Noise",
                    - "URLs",
                    - "Filenames",
                    - "ForeignWords",
                    - "Hashtags"
                    - 'TargetFrequency',
                    - 'NeighborFrequency'.

        See more details for these scores `here
        <http://ldtoolkit.space/ldscores/>`_.

        Returns:
            (None): the annotated neighbors file will be written to disk
                together with the experiment metadata.

        """

        super(AnnotateVectorNeighborhoods, self).__init__(
            experiment_name=experiment_name, extra_metadata=extra_metadata, \
            overwrite=overwrite, embeddings=None, output_dir=output_dir,
            dataset=None, experiment_subfolder="neighbors_annotated")

        if ldt_analyzer:
            global analyzer
            analyzer = ldt_analyzer

        self.metadata["task"] = "annotate_neighbors"
        self.metadata["uuid"] = str(uuid.uuid4())
        self.metadata["ldt_config"] = config
        self.metadata["output_dir"] = self.output_dir
        self._load_dataset(dataset=None)
        neighbors_metadata_path = self.output_dir.replace(
            "neighbors_annotated", "neighbors")
        neighbors_metadata_path = os.path.join(neighbors_metadata_path,
                                               "metadata.json")
        if not os.path.isfile(neighbors_metadata_path):
            raise IOError("The metadata for the neighborhood generation task "
                          "was not found at "+neighbors_metadata_path)
        else:
            self.metadata["neighbors_metadata_path"] = neighbors_metadata_path
            neighbors_metadata = load_json(neighbors_metadata_path)
            self.metadata["embeddings"] = neighbors_metadata["embeddings"]
            self.embeddings = []
            for embedding in self.metadata["embeddings"]:
                self.embeddings.append(embedding["path"])

        self.message = "Starting LD annotation. This will take a while for " \
                       "the first files, but the remainder should go faster, " \
                       "because many neighbor pairs will be the same."

        self.metadata["failed_pairs"] = []
        self.metadata["missed_pairs"] = []
        self.metadata["total_pairs"] = 0

        self.supported_vars = ["SharedPOS", "SharedMorphForm",
                               "SharedDerivation", "NonCooccurring",
                               "GDeps", "TargetFrequency",
                               "NeighborFrequency", "Associations",
                               "ShortestPath", "Synonyms", "Antonyms",
                               "Meronyms", "Hyponyms", "Hypernyms",
                               "OtherRelations", "Numbers", "ProperNouns",
                               "Misspellings", "URLs", "Filenames",
                               "ForeignWords", "Hashtags", "Noise"]

        self.continuous_vars = ['ShortestPath', 'TargetFrequency',
                                'NeighborFrequency']

        corpus_specific = ["NonCooccurring", "TargetFrequency", "NeighborFrequency"]
        if not config["corpus"]:
            for i in [self.supported_vars, self.continuous_vars]:
                i = [x for x in i if not i in corpus_specific]

        self.binary_vars = [x for x in self.supported_vars if not \
            x in self.continuous_vars]

        ld_scores_error = "The ld_scores argument is invalid. It should be " \
                          "'all' for all supported relations, or a list with " \
                          "one or more of the following values:\n" + \
                          ", ".join(self.supported_vars)

        if ld_scores == "all":
            self._ld_scores = self.supported_vars

        elif ld_scores == "main":
            exclude = ["ShortestPath", "URLs", "Filenames", "Hashtags",
                       "Noise"]
            if not config["corpus"]:
                exclude += ["NonCooccurring", "GDeps", "TargetFrequency",
                            "NeighborFrequency"]
            self._ld_scores = [x for x in self.supported_vars if not x in
                                                                     exclude]
        else:
            if isinstance(ld_scores, list):
                unsupported = [x for x in ld_scores if not
                               x in self.supported_vars]
                if unsupported:
                    raise ValueError(ld_scores_error)
                else:
                    self._ld_scores = [x for x in self.supported_vars if x
                                       in ld_scores]
            else:
                raise ValueError(ld_scores_error)

    # removing distributional variables according to config
        if not gdeps:
            if "GDeps" in self._ld_scores:
                self._ld_scores.remove("GDeps")
        if not cooccurrence:
            if "NonCooccurring" in self._ld_scores:
                self._ld_scores.remove("NonCooccurring")
        if not config["corpus"]:
            for i in ["NonCooccurring", "TargetFrequency",
                      "NeighborFrequency"]:
                if i in self._ld_scores:
                    self._ld_scores.remove(i)

        self.metadata["ld_scores"] = self._ld_scores
        self.metadata["continuous_vars"] = self.continuous_vars
        self.metadata["binary_vars"] = self.binary_vars
        #todo remove them when writing out the final metadata



    def _load_dataset(self, dataset):
        """Dataset for generating vector neighborhoods was already processed in
        the previous stage of the experiment, so nothing needs to be done
        here."""
        pass


        # print(f" * Processing {len(source_df)} word pairs")
        #
        # chunk_size = 10000
        #
        # list_df = SplitList(source_df, chunk_size)  #todo hardcoded size of chunks
        #         #
        # bar = progressbar.ProgressBar(max_value=len(list_df))
        # for i in range(len(list_df)):
        #     bar.update(i)
        #     df_slice = list_df[i]
        #     processed_dict = Parallel(n_jobs=4)(delayed(label_word_pair)(row, cols_tuple) for row in df_slice)



    def _process(self, embeddings_path):

        # self.prior_data = collect_prior_data(self.output_dir)

        global prior_data
        prior_data = collect_prior_data(self.metadata["output_dir"])

        global metadata
        metadata=self.metadata

        global analyzer
        analyzer = init_analyzer(metadata)

        filename = self.get_fname_for_embedding(embeddings_path)
        neighbor_file_path = os.path.join(self.output_dir.replace(
            "neighbors_annotated", "neighbors"), filename+".tsv")
        print("Annotating "+neighbor_file_path)

        input_df = pd.read_csv(neighbor_file_path, header=0, sep="\t")
        self.metadata["total_pairs"] += len(input_df)
        dicts = input_df.to_dict(orient="records")

        # for i in tqdm(range(len(dicts))):

        # dicts = Parallel(n_jobs=2)(delayed(self._process_one_dict)(i) for i in dicts)
        # dicts = [self._process_one_dict(i) for i in dicts]

        # worked
        pool = ProcessingPool(nodes=config["experiments"]["multiprocessing"])
        dicts = pool.map(_process_one_dict, dicts)
        # p = Pool(2, initializer(metadata))
        # dicts = p.map(_process_one_dict, dicts)


        # pool = Pool(2)  # on 8 processors
        # dicts = pool.map(self._process_one_dict, dicts)
        # pool.close()
        # pool.join()

        # dicts = Parallel(n_jobs=2)(delayed(_process_one_dict)(i) for i in dicts)

        output_df = pd.DataFrame(dicts,
                                 columns=["Target", "Rank", "Neighbor",
                                          "Similarity"]+self._ld_scores)

        output_df.to_csv(os.path.join(self.output_dir, filename+".tsv"),
                         index=False, sep="\t")


    def _postprocess_metadata(self):
        """Helper method for logging unique failed target:neighbor pairs and
        calculating the overall coverage (considered as number of non-unique
        pairs for which dictionary data was successfully found)."""

        del self.metadata["continuous_vars"]
        del self.metadata["binary_vars"]
        del self.metadata["failed_pairs"]
        del self.metadata["missed_pairs"]

        # total_fails = self.metadata["failed_pairs"] + self.metadata[
        #     "missed_pairs"]
        # total_fails = list(set(total_fails))
        # self.metadata["coverage"] = \
        #     1 - round(len(total_fails) / self.metadata["total_pairs"], 2)


def collect_prior_data(output_dir):
    """Helper for collecting all the previously processed data (useful in
    case a large experiment is interrupted in the middle, as many word pairs
    repeat across different embeddings).

    Args:
        output_dir (str): the path where the previous results have been saved.

    Returns:
         (dict): a dictionary with previously computed word relations,
         with similarity and rank data removed. The keys are target:neighbor
         pairs.

    """
    processed_files = os.listdir(output_dir)
    if "metadata.json" in processed_files:
        processed_files.remove("metadata.json")
    prior_res = {}
    for f in processed_files:
        input_df = pd.read_csv(os.path.join(output_dir, f), header=0, sep="\t")
        del input_df["Rank"]
        del input_df["Similarity"]
        dicts = input_df.to_dict(orient="records")
        for pair in dicts:
            prior_res[pair["Target"]+":"+pair["Neighbor"]] = pair
    return prior_res

def collect_targets_and_neighbors(output_dir):
    neighbors_dir = output_dir.strip("metadata.json")
    neighbor_files = os.listdir(neighbors_dir)
    if "metadata.json" in neighbor_files:
        neighbor_files.remove("metadata.json")
    res = []
    for f in neighbor_files:
        input_df = pd.read_csv(os.path.join(neighbors_dir, f), header=0, sep="\t")
        res += list(input_df["Target"])
        res += list(input_df["Neighbor"])
    return list(set(res))

def init_analyzer(metadata, analyzer=None):

    wordlist = collect_targets_and_neighbors(metadata["neighbors_metadata_path"])

    if analyzer:
        # todo move this to RelationsInPair
        if "GDeps" in metadata["ld_scores"] and config["corpus"]:
            ldt_analyzer._distr_dict._reload_resource(resource="gdeps",
                                                      wordlist=wordlist)
            ldt_analyzer._gdeps = True
        if "NonCooccurring" in metadata["ld_scores"] and config["corpus"]:
            ldt_analyzer._distr_dict._reload_resource(resource="cooccurrence",
                wordlist=wordlist)
            ldt_analyzer._cooccurrence = True

        return analyzer
    else:
        # setting up default ldt resources to be used
        normalizer = Normalization(language="English",
                                   order=("wordnet", "custom"),
                                   lowercasing=True)
        derivation = DerivationAnalyzer()
        lex_dict = MetaDictionary()

        analyzer = RelationsInPair(normalizer=normalizer,
                                   derivation_dict=derivation,
                                   lex_dict=lex_dict,
                                   gdeps="GDeps" in metadata["ld_scores"],
                                   cooccurrence="NonCooccurring" in metadata["ld_scores"],
                                   wordlist=wordlist)
        return analyzer

def _process_one_dict(col_dict):

    # for i in range(len(dicts)):
    # col_dict = dicts[i]
    neighbor = col_dict["Neighbor"]
    target = col_dict["Target"]
    if target + ":" + neighbor in prior_data:
        col_dict.update(prior_data[target + ":" + neighbor])
    else:
        relations = analyzer.analyze(target, neighbor)
        if not relations:
            metadata["failed_pairs"].append(tuple([target, neighbor]))
        else:
            if not "Missing" in relations:
                to_check_continuous = metadata["continuous_vars"]
                to_check_binary = metadata["binary_vars"]
            else:
                # print(target, neighbor)
                to_check_binary = [x for x in ["NonCooccurring", "GDeps"] if
                                   x in metadata["ld_scores"]]
                to_check_continuous = [x for x in
                                       ["TargetFrequency", "NeighborFrequency"]
                                       if x in metadata["ld_scores"]]
                metadata["missed_pairs"].append(tuple([target, neighbor]))
            for i in to_check_continuous:
                if i in relations:
                    col_dict[i] = relations[i]
            for i in to_check_binary:
                col_dict[i] = i in relations
    # print(col_dict)
    return col_dict

def initializer(metadata):
    global analyzer
    analyzer = init_analyzer(metadata)

if __name__ == '__main__':
    annotation = AnnotateVectorNeighborhoods(experiment_name="testing",
                                             overwrite=True)
    # global analyzer
    # analyzer = init_analyzer(annotation.metadata)

    annotation.get_results()
