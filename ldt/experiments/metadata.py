# -*- coding: utf-8 -*-
"""General infrastructure for experiments with automatically logged metadata.

LDT uses the metadata framework developed in the vecto library: the data
for each resource (embeddings, datasets) and experiment are contained in a
unique folder that contains a metadata.json file. Its contents depend on the
type of the resource. See `Vecto documentation
<https://vecto.readthedocs.io/en/docs/tutorial/metadata.html#the-embeddings
-metadata>`_for more details.
Metadata for all resources used in the experiment are automatically included
with the metadata for that experiment, to simplify analysis and improve
reproducibility of experiments. Each resource/experiment also has a UUID.

Todo:

    * distinct filenames from varying parameters and model names
    * testing the resuming of an experiment and detecting unprocessed files

"""

import os
import datetime
import abc

import json
from vecto.utils.data import load_json

from ldt import __version__


class Experiment(metaclass=abc.ABCMeta):
    """The top-level class for all experiments that provides the basic
    infrastructure. All specific experiment types must inherit from it."""

    # pylint: disable = too-many-arguments
    def __init__(self, experiment_name=None, extra_metadata=None,
                 embeddings=None, dataset=None, output_dir=None,
                 overwrite=False, experiment_subfolder=None):
        """ Initializing an Experiment.

        Args:
            experiment_name (str): the human-readable name of an experiment
                (e.g. "Profiling CBOW with window size 2-10")
            extra_metadata (dict): any extra fields to be added to the
                experiment metadata (overwriting any previously existing fields)
            embeddings (list of str or None): a list of paths to input
                data (each containing a metadata.json file). If set to None,
                the config parameters will be ignored (for experiments where
                embedding metadata has already been processed and can be just
                copied over from the previous step.)
            output_dir (str): the *existing* path for saving the *subfolder*
                named with the specified experiment_name, where the output data
                and metadata.json file will be saved.
            dataset (str): the location of the dataset to be used in the
                experiment.
            overwrite (bool): if True, any previous data for the same
                experiment will be overwritten, and the experiment will be
                re-started. If metadata from previous experiment is not
                found, this setting is disregarded.
            experiment_subfolder (str): if provided, the experiment results
                will be saved to this subfolder of the "experiments" folder
        """

        if not isinstance(experiment_name, str):
            raise ValueError("Please specify experiment_name argument: a short "
                             "description of the experiment you're conducting.")

        self.output_dir = check_output(output_dir, experiment_subfolder,
                                       experiment_name)

        if embeddings:
            self.embeddings = check_input(input_data=embeddings)

        self._overwrite = overwrite
        if self._overwrite:
            self._init_metadata(embeddings)

        else:
            metadata_path = os.path.join(self.output_dir, "metadata.json")
            if os.path.isfile(metadata_path):
                self._metadata = load_json(metadata_path)
            else:
                self._init_metadata(embeddings)
                self._overwrite=True

        self._load_dataset(dataset=dataset)
        if isinstance(extra_metadata, dict):
            self._metadata.update(extra_metadata)

    def _init_metadata(self, embeddings):
        """Metadata Init helper"""
        self._metadata = {}

        self._metadata["timestamp"] = {}
        self._metadata["version"] = "ldt v. "+__version__
        self._metadata["class"] = "experiment"
        if hasattr(self, "embeddings"):
            self._metadata["embeddings"] = []
            for embedding in embeddings:
                meta_path = os.path.join(embedding, "metadata.json")
                if os.path.isfile(meta_path):
                    embedding_metadata = load_json(meta_path)
                    embedding_metadata["path"] = embedding
                    self._metadata["embeddings"].append(embedding_metadata)
                else:
                    self._metadata["embeddings"].append(embedding)


    @abc.abstractmethod
    def _load_dataset(self, dataset):
        """Abstract method for experiment-specific helper methods that load
        the input data"""
        pass

    @abc.abstractmethod
    def _process(self, embeddings_path):
        """Abstract method for experiment-specific main methods that specify
        the procedure to be performed on each embedding. These methods are
        responsible for both processing and saving results for individual
        files, and incorporating any existing metadata for those resources"""
        raise NotImplementedError

    def save_metadata(self):
        """Saving the metadata for the given experiment"""
        with open(os.path.join(self.output_dir, "metadata.json"), "w") as path:
            json.dump(self._metadata, fp=path, ensure_ascii=False, indent=4,
                      sort_keys=False, allow_nan=True)

    def _check_uuid_in_metadata(self, field, path):
        """Helper method to determine if a given embedding does have
        associated metadata"""
        for i in self._metadata[field]:
            if i["path"] == path and "uuid" in i:
                return i["uuid"]
        return False


    def get_results(self):
        """The basic routine for processing embeddings one-by-one, and saving
        the timestamps of when each file was started and finished."""
        input_data = self.find_unprocessed_files()
        self.embeddings = input_data
        if self.embeddings:
            if self.message:
                print(self.message)

        for i in self.embeddings:

            uuid = self._check_uuid_in_metadata(field="embeddings", path=i)
            if uuid:
                self._metadata["timestamp"][uuid] = {}
                self._metadata["timestamp"][uuid]["start_time"] = \
                    datetime.datetime.now().isoformat()
            else:
                self._metadata["timestamp"][i]["start_time"] = \
                    datetime.datetime.now().isoformat()

            self._process(embeddings_path=i)
            if uuid:
                self._metadata["timestamp"][uuid]["end_time"] = \
                    datetime.datetime.now().isoformat()
            else:
                self._metadata["timestamp"][i]["end_time"] = \
                    datetime.datetime.now().isoformat()
            self._postprocess_metadata()
            self.save_metadata()

    def find_unprocessed_files(self):
        """Helper method for determining which embeddings have already been
        processed."""
        if self._overwrite:
            return self.embeddings
        else:
            unprocessed = self.embeddings
            for path in self.embeddings:
                uuid = self._check_uuid_in_metadata(field="embeddings", path=path)
                if uuid:
                    if uuid in self._metadata["timestamp"]:
                        unprocessed.remove(path)
                else:
                    if path in self._metadata["timestamp"]:
                        unprocessed.remove(path)
            return unprocessed

    def _postprocess_metadata(self):
        """Helper method for experiments that require extra operations on
        metadata once the processing has been complete"""
        pass

def check_input(input_data):
    """Helper function that makes sure that all input paths are valid."""
    if isinstance(input_data, list):
        # check that all input paths exist
        for i in input_data:
            if not os.path.exists(i):
                raise ValueError("Path", i, "does not exist.")
    return input_data

def check_output(output_dir, experiment_subfolder, experiment_name):
    """Helper function that makes sure that all output paths are valid."""
    if not isinstance(output_dir, str) or not os.path.isdir(output_dir):
        raise ValueError("Please specify output_dir argument: the "
                         "existing path where the output data for "
                         "experiment '" + experiment_name + "' will be saved.")
    else:
        if " " in experiment_name:
            experiment_name = experiment_name.replace(" ", "_")
        if experiment_subfolder:
            full_path = os.path.join(output_dir, experiment_subfolder)
            if not os.path.isdir(full_path):
                os.mkdir(full_path)
            full_path = os.path.join(full_path, experiment_name)
            if not os.path.isdir(full_path):
                os.mkdir(full_path)
        else:
            full_path = os.path.join(output_dir, experiment_name)
            if not os.path.isdir(full_path):
                os.mkdir(full_path)
    return full_path



def generate_identifiable_filenames():
    """TBD"""
    pass


