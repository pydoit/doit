import os
import unittest

import doit
from doit.loader import get_module
from tests.support import RestoreCwdMixin


class TestGetInitialWorkdir(RestoreCwdMixin, unittest.TestCase):
    def test_get_initial_workdir(self):
        initial_wd = os.getcwd()
        fileName = os.path.join(os.path.dirname(__file__), "..", "tests",
                                "loader_sample.py")
        cwd = os.path.normpath(os.path.join(os.path.dirname(__file__), "..",
                                             "tests", "data"))
        self.assertNotEqual(cwd, initial_wd)  # make sure test is not too easy
        get_module(fileName, cwd)
        self.assertEqual(os.getcwd(), cwd)
        self.assertEqual(doit.get_initial_workdir(), initial_wd)
