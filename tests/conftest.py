import os

import py

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


# fixture for "doit.db". create/remove for every test
def pytest_funcarg__depfile(request):
    def create_depfile():
        if hasattr(request, 'param'):
            dep_class = request.param
        else:
            dep_class = Dependency

        # copied from tempdir plugin
        name = request._pyfuncitem.name
        name = py.std.re.sub("[\W]", "_", name)
        my_tmpdir = request.config._tmpdirhandler.mktemp(name, numbered=True)
        return dep_class(os.path.join(my_tmpdir.strpath, "testdb"))

    def remove_depfile(depfile):
        if not depfile._closed:
            depfile.close()
        remove_db(depfile.name)

    return request.cached_setup(
        setup=create_depfile,
        teardown=remove_depfile,
        scope="function")


def pytest_funcarg__cwd(request):
    """set cwd to parent folder of this file."""
    def set_cwd():
        cwd = {}
        cwd['previous'] = os.getcwd()
        cwd['current'] = os.path.abspath(os.path.dirname(__file__))
        os.chdir(cwd['current'])
        return cwd
    def restore_cwd(cwd):
        os.chdir(cwd['previous'])
    return request.cached_setup(
        setup=set_cwd,
        teardown=restore_cwd,
        scope="function")


# create a list of sample tasks
def tasks_sample():
    tasks_sample = [
        Task("t1", [""], doc="t1 doc string"),
        Task("t2", [""], doc="t2 doc string"),
        Task("g1", None, doc="g1 doc string"),
        Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
        Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
        Task("t3", [""], doc="t3 doc string")]
    tasks_sample[2].task_dep = ['g1.a', 'g1.b']
    return tasks_sample
