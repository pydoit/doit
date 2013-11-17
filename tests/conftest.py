import os
import time
import multiprocessing
import six
if six.PY3: # pragma: no cover
    from dbm import whichdb
else:
    from whichdb import whichdb


import py
import pytest

from doit.dependency import Dependency
from doit.task import Task


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.join(os.path.dirname(__file__), relativePath)

# fixture to create a sample file to be used as file_dep
@pytest.fixture
def dependency1(request):
    path = get_abspath("data/dependency1")
    if os.path.exists(path): os.remove(path)
    ff = open(path, "w")
    ff.write("whatever" + str(time.asctime()))
    ff.close()

    def remove_dependency():
        if os.path.exists(path):
            os.remove(path)
    request.addfinalizer(remove_dependency)

    return path


# fixture for "doit.db". create/remove for every test
def remove_db(filename):
    """remove db file from anydbm"""
    # dbm on some systems add '.db' on others add ('.dir', '.pag')
    extensions = ['', #dbhash #gdbm
                  '.bak', #dumbdb
                  '.dat', #dumbdb
                  '.dir', #dumbdb #dbm2
                  '.db', #dbm1
                  '.pag', #dbm2
                  ]
    for ext in extensions:
        if os.path.exists(filename + ext):
            os.remove(filename + ext)

# dbm backends use different file extentions
db_ext = {'dbhash': [''],
          'gdbm': [''],
          'dbm': ['.db', '.dir'],
          'dumbdbm': ['.dat'],
          # for python3
          'dbm.ndbm': ['.db'],
          }

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
    dep_file.whichdb = whichdb(dep_file.name)
    dep_file.name_ext = db_ext.get(dep_file.whichdb, [''])

    def remove_depfile():
        if not dep_file._closed:
            dep_file.close()
        remove_db(dep_file.name)
    request.addfinalizer(remove_depfile)

    return dep_file

@pytest.fixture
def depfile_name(request):
    # copied from tempdir plugin
    name = request._pyfuncitem.name
    name = py.std.re.sub("[\W]", "_", name)
    my_tmpdir = request.config._tmpdirhandler.mktemp(name, numbered=True)
    depfile_name = (os.path.join(my_tmpdir.strpath, "testdb"))

    def remove_depfile():
        remove_db(depfile_name)
    request.addfinalizer(remove_depfile)

    return depfile_name


@pytest.fixture
def restore_cwd(request):
    """restore cwd to its initial value after test finishes."""
    previous = os.getcwd()
    def restore_cwd():
        os.chdir(previous)
    request.addfinalizer(restore_cwd)


# create a list of sample tasks
def tasks_sample():
    tasks_sample = [
        Task("t1", [""], doc="t1 doc string"),
        Task("t2", [""], file_dep=['tests/data/dependency1'],
             doc="t2 doc string"),
        Task("g1", None, doc="g1 doc string"),
        Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
        Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
        Task("t3", [""], doc="t3 doc string", task_dep=["t1"])
        ]
    tasks_sample[2].task_dep = ['g1.a', 'g1.b']
    return tasks_sample



# mokey patch multiprocessing to enable  code coverage
# NOTE: doesnt work with pytest-xdist (actually execnet)
def coverage_multiprocessing_process(): # pragma: no cover
    try:
        import coverage as _coverage
        _coverage
    except:
        return

    from coverage.collector import Collector
    from coverage.control import coverage
    # detect if coverage was running in forked process
    if Collector._collectors:
        original = multiprocessing.Process._bootstrap
        class Process_WithCoverage(multiprocessing.Process):
            def _bootstrap(self):
                cov = coverage(data_suffix=True)
                cov.start()
                try:
                    return original(self)
                finally:
                    cov.stop()
                    cov.save()
        return Process_WithCoverage

ProcessCoverage = coverage_multiprocessing_process()
if ProcessCoverage:
    multiprocessing.Process = ProcessCoverage
