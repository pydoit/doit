import os

import doit
from doit.loader import get_module


def test_get_initial_workdir(restore_cwd):
    initial_wd = os.getcwd()
    fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
    cwd = os.path.normpath(os.path.join(os.path.dirname(__file__), "data"))
    assert cwd != initial_wd # make sure test is not too easy
    get_module(fileName, cwd)
    assert os.getcwd() == cwd, os.getcwd()
    assert doit.get_initial_workdir() == initial_wd

