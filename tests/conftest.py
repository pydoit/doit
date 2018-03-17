import os
import time
from dbm import whichdb

import py
import pytest

from doit.dependency import DbmDB, Dependency, MD5Checker
from doit.task import Task


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.join(os.path.dirname(__file__), relativePath)

# fixture to create a sample file to be used as file_dep
def dependency_factory(relative_path):

    @pytest.fixture
    def dependency(request):
        path = get_abspath(relative_path)
        if os.path.exists(path): os.remove(path)
        ff = open(path, "w")
        ff.write("whatever" + str(time.asctime()))
        ff.close()

        def remove_dependency():
            if os.path.exists(path):
                os.remove(path)
        request.addfinalizer(remove_dependency)

        return path

    return dependency


dependency1 = dependency_factory("data/dependency1")
dependency2 = dependency_factory("data/dependency2")

# fixture to create a sample file to be used as file_dep
@pytest.fixture
def target1(request):
    path = get_abspath("data/target1")
    if os.path.exists(path): # pragma: no cover
        os.remove(path)
    def remove_path():
        if os.path.exists(path):
            os.remove(path)
    request.addfinalizer(remove_path)
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
def dep_manager(request):
    if hasattr(request, 'param'):
        dep_class = request.param
    else:
        dep_class = DbmDB

    # copied from tempdir plugin
    name = request._pyfuncitem.name
    name = py.std.re.sub("[\W]", "_", name)
    my_tmpdir = request.config._tmpdirhandler.mktemp(name, numbered=True)
    dep_file = Dependency(dep_class, os.path.join(my_tmpdir.strpath, "testdb"))
    dep_file.whichdb = whichdb(dep_file.name) if dep_class is DbmDB else 'XXX'
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
        # 0
        Task("t1", [""], doc="t1 doc string"),
        # 1
        Task("t2", [""], file_dep=['tests/data/dependency1'],
             doc="t2 doc string"),
        # 2
        Task("g1", None, doc="g1 doc string", has_subtask=True),
        # 3
        Task("g1.a", [""], doc="g1.a doc string", subtask_of='g1'),
        # 4
        Task("g1.b", [""], doc="g1.b doc string", subtask_of='g1'),
        # 5
        Task("t3", [""], doc="t3 doc string", task_dep=["t1"])
        ]
    tasks_sample[2].task_dep = ['g1.a', 'g1.b']
    return tasks_sample


def tasks_bad_sample():
    """Create list of tasks that cause errors."""
    bad_sample = [
        Task("e1", [""], doc='e4 bad file dep', file_dep=['xxxx'])
    ]
    return bad_sample


def CmdFactory(cls, outstream=None, task_loader=None, dep_file=None,
               backend=None, task_list=None, sel_tasks=None,
               dep_manager=None, config=None, cmds=None):
    """helper for test code, so test can call _execute() directly"""
    cmd = cls(task_loader=task_loader, config=config, cmds=cmds)

    if outstream:
        cmd.outstream = outstream
    if backend:
        assert backend == "dbm" # the only one used on tests
        cmd.dep_manager = Dependency(DbmDB, dep_file, MD5Checker)
    elif dep_manager:
        cmd.dep_manager = dep_manager
    cmd.dep_file = dep_file    # (str) filename usually '.doit.db'
    cmd.task_list = task_list  # list of tasks
    cmd.sel_tasks = sel_tasks  # from command line or default_tasks
    return cmd
