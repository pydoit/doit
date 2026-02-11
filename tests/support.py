"""Shared test utilities for unittest-based tests (rut).

Provides mixins and helper functions equivalent to tests/conftest.py
but without any pytest dependency.
"""
import os
import time
import tempfile
import shutil
import itertools
from dbm import whichdb

from doit.dependency import Dependency, MD5Checker
from doit.dependency import DbmDB, JsonDB, SqliteDB
from doit.task import Task
from doit.cmd_base import get_loader


# ---------------------------------------------------------------------------
# Plain helpers (copied from tests/conftest.py — already pytest-free)
# ---------------------------------------------------------------------------

def get_abspath(relative_path):
    """Return absolute file path relative to tests/ directory."""
    return os.path.join(os.path.dirname(__file__), relative_path)


# dbm backends use different file extensions
db_ext = {
    'dbm.ndbm': ['.db'],
    'dbm.dump': ['.dat', '.dir', '.bak'],
    'dbm.gnu': [''],
}


def remove_all_db(filename):
    """Remove db file from anydbm (all possible extensions)."""
    for ext in itertools.chain.from_iterable(db_ext.values()):
        if os.path.exists(filename + ext):
            try:
                os.remove(filename + ext)
            except PermissionError:
                pass


backend_map = {
    'dbm': DbmDB,
    'dbm.gnu': DbmDB,
    'dbm.ndbm': DbmDB,
    'dbm.dumb': DbmDB,
    'json': JsonDB,
    'sqlite3': SqliteDB,
}


def tasks_sample(dep1=None):
    """Create a list of sample tasks."""
    file_dep = dep1 if dep1 else 'tests/data/dependency1'
    sample = [
        Task("t1", [""], doc="t1 doc string",
             params=[{'name': 'arg1', 'short': 'a', 'long': 'arg1',
                       'default': 'default_value'}]),
        Task("t2", [""], file_dep=[file_dep], doc="t2 doc string"),
        Task("g1", None, doc="g1 doc string", has_subtask=True),
        Task("g1.a", [""], doc="g1.a doc string", subtask_of='g1'),
        Task("g1.b", [""], doc="g1.b doc string", subtask_of='g1'),
        Task("t3", [""], doc="t3 doc string", task_dep=["t1"]),
    ]
    sample[2].task_dep = ['g1.a', 'g1.b']
    return sample


def tasks_bad_sample():
    """Create list of tasks that cause errors."""
    return [Task("e1", [""], doc='e4 bad file dep', file_dep=['xxxx'])]


def CmdFactory(cls, outstream=None, task_loader=None, dep_file=None,
               backend=None, task_list=None, sel_tasks=None,
               sel_default_tasks=False, dep_manager=None, config=None,
               cmds=None):
    """Helper for test code, so test can call _execute() directly."""
    loader = get_loader(config, task_loader, cmds)
    cmd = cls(task_loader=loader, config=config, cmds=cmds)
    if outstream:
        cmd.outstream = outstream
    if backend:
        dep_class = backend_map[backend]
        cmd.dep_manager = Dependency(dep_class, dep_file, MD5Checker,
                                     module_name=backend)
    elif dep_manager:
        cmd.dep_manager = dep_manager
    cmd.dep_file = dep_file
    cmd.task_list = task_list
    cmd.sel_tasks = sel_tasks
    cmd.sel_default_tasks = sel_default_tasks
    return cmd


# ---------------------------------------------------------------------------
# Mixins (use cooperative super() for composability)
# ---------------------------------------------------------------------------

class DepManagerMixin:
    """Provides self.dep_manager (DbmDB backend) with cleanup."""

    def setUp(self):
        super().setUp()
        self._dep_tmpdir = tempfile.mkdtemp(prefix='doit-test-')
        filename = os.path.join(self._dep_tmpdir, 'testdb')
        self.dep_manager = Dependency(DbmDB, filename)
        if whichdb(self.dep_manager.name):
            self.dep_manager.whichdb = whichdb(self.dep_manager.name)
        else:
            self.dep_manager.whichdb = 'dbm'
        self.dep_manager.name_ext = db_ext.get(
            self.dep_manager.whichdb, [''])

    def tearDown(self):
        if not self.dep_manager._closed:
            self.dep_manager.close()
        remove_all_db(self.dep_manager.name)
        shutil.rmtree(self._dep_tmpdir, ignore_errors=True)
        super().tearDown()


class DepfileNameMixin:
    """Provides self.depfile_name (path string) with cleanup."""

    def setUp(self):
        super().setUp()
        self._depfile_tmpdir = tempfile.mkdtemp(prefix='doit-test-')
        self.depfile_name = os.path.join(self._depfile_tmpdir, 'testdb')

    def tearDown(self):
        remove_all_db(self.depfile_name)
        shutil.rmtree(self._depfile_tmpdir, ignore_errors=True)
        super().tearDown()


class DependencyFileMixin:
    """Provides self.dependency1 and self.dependency2 file paths."""

    def setUp(self):
        super().setUp()
        self.dependency1 = get_abspath("data/dependency1")
        self._write_dep(self.dependency1)
        self.dependency2 = get_abspath("data/dependency2")
        self._write_dep(self.dependency2)

    def _write_dep(self, path):
        if os.path.exists(path):
            os.remove(path)
        with open(path, "w") as f:
            f.write("whatever" + str(time.asctime()))

    def tearDown(self):
        for p in (self.dependency1, self.dependency2):
            if os.path.exists(p):
                os.remove(p)
        super().tearDown()


class RestoreCwdMixin:
    """Restores cwd after each test."""

    def setUp(self):
        super().setUp()
        self._original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._original_cwd)
        super().tearDown()
