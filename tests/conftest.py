import os

import py
import pytest

from doit.dependency import Dependency
from doit.task import Task

TESTDB = os.path.join(os.path.dirname(__file__), "testdb")


def remove_db(filename):
    """remove db file from anydbm"""
    extensions = ['', #dbhash #gdbm
                  '.bak', #dumbdb
                  '.dat', #dumbdb
                  '.dir', #dumbdb #dbm
                  '.db', #dbm
                  '.pag', #dbm
                  ]
    for ext in extensions:
        if os.path.exists(filename + ext):
            os.remove(filename + ext)


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.join(os.path.dirname(__file__), relativePath)

# fixture to create a sample file to be used as file_dep
@pytest.fixture
def dependency1(request):
    path = get_abspath("data/dependency1")
    if os.path.exists(path): os.remove(path)
    ff = open(path, "w")
    ff.write("whatever")
    ff.close()

    def remove_dependency():
        if os.path.exists(path):
            os.remove(path)
    request.addfinalizer(remove_dependency)

    return path


# fixture for "doit.db". create/remove for every test
@pytest.fixture
def depfile(request):
    if hasattr(request, 'param'):
        dep_class = request.param
    else:
        dep_class = Dependency

    # copied from tempdir plugin
    name = request._pyfuncitem.name
    name = py.std.re.sub("[\W]", "_", name)
    my_tmpdir = request.config._tmpdirhandler.mktemp(name, numbered=True)
    dep_file = dep_class(os.path.join(my_tmpdir.strpath, "testdb"))

    def remove_depfile():
        if not dep_file._closed:
            dep_file.close()
        remove_db(dep_file.name)
    request.addfinalizer(remove_depfile)

    return dep_file


@pytest.fixture
def cwd(request):
    """set cwd to parent folder of this file."""
    cwd = {}
    cwd['previous'] = os.getcwd()
    cwd['current'] = os.path.abspath(os.path.dirname(__file__))
    os.chdir(cwd['current'])
    def restore_cwd():
        os.chdir(cwd['previous'])
    request.addfinalizer(restore_cwd)
    return cwd


# create a list of sample tasks
def tasks_sample():
    tasks_sample = [
        Task("t1", [""], doc="t1 doc string"),
        Task("t2", [""], file_dep=['tests/data/dependency1'],
             doc="t2 doc string"),
        Task("g1", None, doc="g1 doc string"),
        Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
        Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
        Task("t3", [""], doc="t3 doc string")]
    tasks_sample[2].task_dep = ['g1.a', 'g1.b']
    return tasks_sample
