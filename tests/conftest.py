import os
import time
import itertools
from dbm import whichdb

import pytest

from doit.dependency import Dependency, MD5Checker
from doit.dependency import DbmDB, JsonDB, SqliteDB
from doit.task import Task
from doit.cmd_base import get_loader


# compatibility to run tests even if xdist is not installed
try:
    from xdist import plugin
    plugin
except:
    @pytest.fixture
    def worker_id():
        return


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.join(os.path.dirname(__file__), relativePath)


# fixture to create a sample file to be used as file_dep
def dependency_factory(relative_path):

    @pytest.fixture
    def dependency(request, worker_id):
        path = get_abspath(relative_path)
        if worker_id:
            path += f'_{worker_id}'
        if os.path.exists(path):  # pragma: no cover
            os.remove(path)
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
    if os.path.exists(path):  # pragma: no cover
        os.remove(path)
    def remove_path():
        if os.path.exists(path):
            os.remove(path)
    request.addfinalizer(remove_path)
    return path


# dbm backends use different file extensions
db_ext = {
    'dbm.ndbm': ['.db'],
    'dbm.dump': ['.dat', '.dir', '.bak'],
    'dbm.gnu': [''],
}

# fixture for "doit.db". create/remove for every test
def remove_all_db(filename):
    """remove db file from anydbm"""
    for ext in itertools.chain.from_iterable(db_ext.values()):
        if os.path.exists(filename + ext):
            os.remove(filename + ext)

backend_map = {
    'dbm': DbmDB,
    'dbm.gnu': DbmDB,
    'dbm.ndbm': DbmDB,
    'dbm.dumb': DbmDB,
    'json': JsonDB,
    'sqlite3': SqliteDB,
}

def dep_manager_fixture(request, tmp_path_factory, backend_name):
    filename = str(tmp_path_factory.mktemp('x', True) / 'testdb')
    dep_class = backend_map[backend_name]
    try:
        if backend_name.startswith('dbm.'):
            dep_file = Dependency(dep_class, filename, module_name=backend_name)
        else:
            dep_file = Dependency(dep_class, filename)
    except ImportError:
        pytest.skip(f'"{backend_name}" not available.')
    if backend_name == 'dbm':
        dep_file.whichdb = whichdb(dep_file.name)
    else:
        dep_file.whichdb = backend_name
    dep_file.name_ext = db_ext.get(dep_file.whichdb, [''])

    def remove_depfile():
        if not dep_file._closed:
            dep_file.close()
        remove_all_db(dep_file.name)
    request.addfinalizer(remove_depfile)

    return dep_file


@pytest.fixture
def dep_manager(request, tmp_path_factory):
    return dep_manager_fixture(request, tmp_path_factory, 'dbm')


@pytest.fixture
def depfile_name(request, tmp_path_factory):
    depfile_name = str(tmp_path_factory.mktemp('x', True) / 'testdb')
    def remove_depfile():
        remove_all_db(depfile_name)
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
def tasks_sample(dep1=None):
    file_dep = dep1 if dep1 else 'tests/data/dependency1'
    tasks_sample = [
        # 0
        Task(
            "t1", [""], doc="t1 doc string",
            params=[
                {
                    'name': 'arg1',
                    'short': 'a',
                    'long': 'arg1',
                    'default': 'default_value',
                },
            ]),
        # 1
        Task("t2", [""], file_dep=[file_dep], doc="t2 doc string"),
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
               backend=None, task_list=None, sel_tasks=None, sel_default_tasks=False,
               dep_manager=None, config=None, cmds=None):
    """helper for test code, so test can call _execute() directly"""
    loader = get_loader(config, task_loader, cmds)
    cmd = cls(task_loader=loader, config=config, cmds=cmds)

    if outstream:
        cmd.outstream = outstream
    if backend:
        dep_class = backend_map[backend]
        cmd.dep_manager = Dependency(dep_class, dep_file, MD5Checker, module_name=backend)
    elif dep_manager:
        cmd.dep_manager = dep_manager
    cmd.dep_file = dep_file  # (str) filename usually '.doit.db'
    cmd.task_list = task_list  # list of tasks
    cmd.sel_tasks = sel_tasks  # from command line or default_tasks
    cmd.sel_default_tasks = sel_default_tasks
    return cmd
