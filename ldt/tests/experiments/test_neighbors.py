import unittest

import ldt
import os
import shutil

import json

from ldt.load_config import config

path_to_resources = config["path_to_resources"]

class Tests(unittest.TestCase):
    """
    The tests in this block inspect generating vector neighborhood data.
    """

    @classmethod
    def setUpClass(cls):
        """Setting up the test variables."""
        cls.experiment = ldt.experiments.VectorNeighborhoods(
            experiment_name="testing", overwrite=True, top_n=5)
        cls.experiment.get_results()

    @classmethod
    def tearDownClass(cls):
        """Clearning up the test dir."""
        cls.experiment = None
        dir = os.path.join(config["path_to_resources"], "experiments",
                           "neighbors", "testing")
        shutil.rmtree(dir)

    def test_dir(self):
        """Creation of subfolder per specific experiment"""
        dir = os.path.join(config["path_to_resources"], "experiments",
                           "neighbors", "testing")
        self.assertTrue(os.path.isdir(dir))

    def test_dataset(self):
        """Testing that the vocabulary sample is loaded"""
        self.assertTrue("activism" in self.experiment.dataset)


    def test_metadata(self):
        """Testing that the experiment metadata is saved"""
        metadata_path = os.path.join(config["path_to_resources"],
                                     "experiments", "neighbors", "testing",
                                     "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertTrue("timestamp" in metadata)

    def test_metadata_embeddings(self):
        """Testing that the embeddings metadata is incorporated"""
        metadata_path = os.path.join(config["path_to_resources"],
                                     "experiments", "neighbors", "testing",
                                     "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertTrue("model" in metadata["embeddings"][0])

    def test_metadata_dataset(self):
        """Testing that the dataset metadata is incorporated"""
        metadata_path = os.path.join(config["path_to_resources"],
                                     "experiments", "neighbors", "testing",
                                     "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertTrue("language" in metadata["dataset"])

    def test_metadata_uuid(self):
        """Testing that the dataset metadata is incorporated"""
        metadata_path = os.path.join(config["path_to_resources"],
                                     "experiments", "neighbors", "testing",
                                     "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertTrue("uuid" in metadata and len(metadata["uuid"]) == 36)

    def test_neighbor_extraction(self):
        dir = os.path.join(config["path_to_resources"], "experiments",
                           "neighbors", "testing")
        files = os.listdir(dir)
        fname = ""
        for f in files:
            if "sample_embeddings" in f:
                f = os.path.join(dir, f)
                with open(f, "r") as sample_neighbor_file:
                    data = sample_neighbor_file.readlines()
                    res = 'hurricane\t1\tstorm\t0.9598022699356079\n' in data
                    self.assertTrue(res)
#
# #test that timestamp for each processed file is saved

if __name__ == '__main__':
    unittest.main()
