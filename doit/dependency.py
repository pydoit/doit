"""Manage (save/check) task dependency-on-files data."""

import os
import hashlib
import subprocess
import inspect
import json
from abc import ABC, abstractmethod
from collections import defaultdict
import importlib
import dbm
from enum import Enum

# note: to check which DBM backend is being used:
#   >>> doit dumpdb


class DependencyReason(Enum):
    """Reasons why a task is not up-to-date.

    These are used as keys in DependencyStatus.reasons dict to explain
    why a task needs to be executed.
    """
    # Uptodate callable returned False
    UPTODATE_FALSE = 'uptodate_false'
    # Task has no dependencies (always runs)
    HAS_NO_DEPENDENCIES = 'has_no_dependencies'
    # Target file doesn't exist
    MISSING_TARGET = 'missing_target'
    # File checker class changed
    CHECKER_CHANGED = 'checker_changed'
    # New file dependencies added
    ADDED_FILE_DEP = 'added_file_dep'
    # File dependencies removed
    REMOVED_FILE_DEP = 'removed_file_dep'
    # File dependency doesn't exist
    MISSING_FILE_DEP = 'missing_file_dep'
    # File dependency content changed
    CHANGED_FILE_DEP = 'changed_file_dep'


class StorageKey:
    """Constants for special storage keys used in task state persistence.

    These keys are used in the key-value store to identify different types
    of task metadata. Regular file dependency keys are file paths.
    """
    # Task values dict (returned by actions)
    VALUES = '_values_:'
    # Task result hash for up-to-date checking
    RESULT = 'result:'
    # File checker class name
    CHECKER = 'checker:'
    # List of file dependencies
    DEPS = 'deps:'
    # Task ignore flag
    IGNORE = 'ignore:'


class DatabaseException(Exception):
    """Exception class for whatever backend exception"""
    pass


def get_md5(input_data):
    """return md5 from string or unicode"""
    byte_data = input_data.encode("utf-8")
    return hashlib.md5(byte_data).hexdigest()


def get_file_md5(path):
    """Calculate the md5 sum from file content.

    @param path: (string) file path
    @return: (string) md5
    """
    with open(path, 'rb') as file_data:
        md5 = hashlib.md5()
        block_size = 128 * md5.block_size
        while True:
            data = file_data.read(block_size)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


class JSONCodec():
    """default implmentation for codec used to save individual task's data"""
    def __init__(self):
        self.encoder = json.JSONEncoder()
        self.decoder = json.JSONDecoder()

    def encode(self, data):
        return self.encoder.encode(data)

    def decode(self, data):
        return self.decoder.decode(data)


class ProcessingStateStore(ABC):
    """Abstract base class for task state persistence backends.

    Stores task execution state including:
    - File dependency checksums
    - Task result values
    - Execution timestamps

    All backends must implement this interface for storing and retrieving
    task state. The state is organized by task_id, with each task having
    multiple key-value pairs (e.g., file dependencies, result hashes).
    """

    @abstractmethod
    def set(self, task_id, key, value):
        """Store a value for a task.

        @param task_id: (str) unique task identifier
        @param key: (str) key within the task's data (e.g., file path, 'result:')
        @param value: value to store (must be JSON-serializable)
        """
        pass

    @abstractmethod
    def get(self, task_id, key):
        """Get a stored value.

        @param task_id: (str) unique task identifier
        @param key: (str) key within the task's data
        @return: stored value, or None if not found
        """
        pass

    @abstractmethod
    def in_(self, task_id):
        """Check if task has any stored state.

        @param task_id: (str) unique task identifier
        @return: (bool) True if task has stored state
        """
        pass

    @abstractmethod
    def remove(self, task_id):
        """Remove all state for a task.

        @param task_id: (str) unique task identifier
        """
        pass

    @abstractmethod
    def remove_all(self):
        """Remove all stored state for all tasks."""
        pass

    @abstractmethod
    def dump(self):
        """Persist any pending changes and close resources.

        Called when the dependency manager is closed. Should ensure all
        data is written to persistent storage (if applicable) and release
        any held resources.
        """
        pass


class InMemoryStateStore(ProcessingStateStore):
    """In-memory state store for testing and ephemeral execution.

    This backend stores all state in memory only. State is lost when the
    process exits. Useful for:
    - Testing without file system side effects
    - One-off task execution where persistence isn't needed
    - Programmatic usage where the caller manages state
    """

    def __init__(self, name=None, codec=None, *, module_name=None):
        """Initialize in-memory store.

        @param name: ignored (for API compatibility with file-based stores)
        @param codec: ignored (for API compatibility)
        @param module_name: ignored (for API compatibility)
        """
        self._db = {}
        self.name = name if name else ':memory:'

    def set(self, task_id, key, value):
        if task_id not in self._db:
            self._db[task_id] = {}
        self._db[task_id][key] = value

    def get(self, task_id, key):
        if task_id in self._db:
            return self._db[task_id].get(key)
        return None

    def in_(self, task_id):
        return task_id in self._db

    def remove(self, task_id):
        if task_id in self._db:
            del self._db[task_id]

    def remove_all(self):
        self._db = {}

    def dump(self):
        pass  # Nothing to persist


class JsonDB(ProcessingStateStore):
    """Backend using a single text file with JSON content"""

    def __init__(self, name, codec, *, module_name=None):
        """Open/create a DB file"""
        self.name = name
        self.codec = codec
        if not os.path.exists(self.name):
            self._db = {}
        else:
            self._db = self._load()

    def _load(self):
        """load db content from file"""
        db_file = open(self.name, 'r')
        try:
            try:
                return self.codec.decode(db_file.read())
            except ValueError as error:
                # file contains corrupted json data
                fname = os.path.abspath(self.name)
                msg = (f"{error.args[0]}\nInvalid JSON data in {fname}\n"
                       "To fix this problem, you can just remove the "
                       "corrupted file, a new one will be generated.\n")
                error.args = (msg,)
                raise DatabaseException(msg)
        finally:
            db_file.close()

    def dump(self):
        """save DB content in file"""
        try:
            db_file = open(self.name, 'w')
            db_file.write(self.codec.encode(self._db))
        finally:
            db_file.close()

    def set(self, task_id, dependency, value):
        """Store value in the DB."""
        if task_id not in self._db:
            self._db[task_id] = {}
        self._db[task_id][dependency] = value


    def get(self, task_id, dependency):
        """Get value stored in the DB.

        @return: (string) or (None) if entry not found
        """
        if task_id in self._db:
            return self._db[task_id].get(dependency, None)


    def in_(self, task_id):
        """@return bool if task_id is in DB"""
        return task_id in self._db


    def remove(self, task_id):
        """remove saved dependencies from DB for taskId"""
        if task_id in self._db:
            del self._db[task_id]

    def remove_all(self):
        """remove saved dependencies from DB for all tasks"""
        self._db = {}


def get_dbm_module(mod_name):
    if mod_name:
        return importlib.import_module(mod_name)
    return importlib.import_module('dbm')  # use system default


class DbmDB(ProcessingStateStore):
    """Backend using a DBM file with individual values encoded in JSON

    On initialization all items are read from DBM file and loaded on ``_dbm``.
    During execution whenever an item is read (``get`` method) the `json` value
    is cached on ``_db``.
    If an item is modified ``_db`` is update and the `id` is added
    to the `dirty` set. Only on ``dump`` all dirty items values are encoded
    in json into ``_dbm`` and the DBM file is saved.

    :ivar str name: file name/path
    :ivar module: DBM implementation name one of: 'dbm.gun', 'dbm.ndbm', 'dbm.dumb'.
    :ivar dbm _dbm: items with json encoded values
    :ivar dict _db: items with python-dict as value
    :ivar set dirty: id of modified tasks
    """
    DBM_CONTENT_ERROR_MSG = 'db type could not be determined'

    def __init__(self, name, codec, *, module_name=None):
        """Open/create a DB file"""
        self.name = name
        self.codec = codec
        self.module = get_dbm_module(module_name)
        try:
            self._dbm = self.module.open(self.name, 'c')
        except dbm.error as exception:
            message = str(exception)
            if message == self.DBM_CONTENT_ERROR_MSG:
                # When a corrupted/old format database is found
                # suggest the user to just remove the file
                new_message = (
                    'Dependencies file in %(filename)s seems to use '
                    'an old format or is corrupted.\n'
                    'To fix the issue you can just remove the database file(s) '
                    'and a new one will be generated.'
                    % {'filename': repr(self.name)})
                raise DatabaseException(new_message)
            else:
                # Re-raise any other exceptions
                raise DatabaseException(message)

        self._db = {}
        self.dirty = set()

    def dump(self):
        """save/close DBM file"""
        for task_id in self.dirty:
            self._dbm[task_id] = self.codec.encode(self._db[task_id])
        self._dbm.close()


    def set(self, task_id, dependency, value):
        """Store value in the DB."""
        if task_id not in self._db:
            self._db[task_id] = {}
        self._db[task_id][dependency] = value
        self.dirty.add(task_id)


    def _in_dbm(self, key):
        """
        should be just::
          return key in self._dbm

         for get()/set() key is convert to bytes but not for 'in'
        """
        return key.encode('utf-8') in self._dbm


    def get(self, task_id, dependency):
        """Get value stored in the DB.

        :return: string or None if entry not found
        """
        # optimization, just try to get it without checking it exists
        if task_id in self._db:
            return self._db[task_id].get(dependency, None)
        else:
            try:
                task_data = self._dbm[task_id]
            except KeyError:
                return
            self._db[task_id] = self.codec.decode(task_data.decode('utf-8'))
            return self._db[task_id].get(dependency, None)


    def in_(self, task_id):
        """@return bool if task_id is in DB"""
        return self._in_dbm(task_id) or task_id in self.dirty


    def remove(self, task_id):
        """remove saved dependencies from DB for taskId"""
        if task_id in self._db:
            del self._db[task_id]
        if self._in_dbm(task_id):
            del self._dbm[task_id]
        if task_id in self.dirty:
            self.dirty.remove(task_id)


    def remove_all(self):
        """remove saved dependencies from DB for all tasks"""
        self._db = {}
        self._dbm.close()
        del self._dbm
        self._dbm = self.module.open(self.name, 'n')
        self.dirty = set()



class SqliteDB(ProcessingStateStore):
    """ sqlite3 json backend """

    def __init__(self, name, codec, *, module_name=None):
        self.name = name
        self.codec = codec
        self._conn = self._sqlite3(self.name)
        self._cache = {}
        self._dirty = set()

    def _sqlite3(self, name):
        """Open/create a sqlite3 DB file"""

        # Import sqlite here so it's only imported when required
        import sqlite3
        def dict_factory(cursor, row):
            """convert row to dict"""
            data = {}
            for idx, col in enumerate(cursor.description):
                data[col[0]] = row[idx]
            return data
        def converter(data):
            return self.codec.decode(data.decode('utf-8'))

        sqlite3.register_adapter(list, self.codec.encode)
        sqlite3.register_adapter(dict, self.codec.encode)
        sqlite3.register_converter("json", converter)
        conn = sqlite3.connect(
            name,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            isolation_level='DEFERRED')
        conn.row_factory = dict_factory
        sqlscript = """
            create table if not exists doit (
                task_id text not null primary key,
                task_data json
            );"""
        try:
            conn.execute(sqlscript)
        except sqlite3.DatabaseError as exception:
            new_message = (
                'Dependencies file in %(filename)s seems to use '
                'an bad format or is corrupted.\n'
                'To fix the issue you can just remove the database file(s) '
                'and a new one will be generated.'
                'Original error: %(msg)s'
                % {'filename': repr(name), 'msg': str(exception)})
            raise DatabaseException(new_message)
        return conn

    def get(self, task_id, dependency):
        """Get value stored in the DB.

        @return: (string) or (None) if entry not found
        """
        if task_id in self._cache:
            return self._cache[task_id].get(dependency, None)
        else:
            data = self._cache[task_id] = self._get_task_data(task_id)
            return data.get(dependency, None)

    def _get_task_data(self, task_id):
        data = self._conn.execute('select task_data from doit where task_id=?',
                                  (task_id,)).fetchone()
        return data['task_data'] if data else {}

    def set(self, task_id, dependency, value):
        """Store value in the DB."""
        if task_id not in self._cache:
            self._cache[task_id] = {}
        self._cache[task_id][dependency] = value
        self._dirty.add(task_id)


    def in_(self, task_id):
        if task_id in self._cache:
            return True
        if self._conn.execute('select task_id from doit where task_id=?',
                              (task_id,)).fetchone():
            return True
        return False

    def dump(self):
        """save/close sqlite3 DB file"""
        for task_id in self._dirty:
            self._conn.execute('insert or replace into doit values (?,?)',
                               (task_id, self.codec.encode(self._cache[task_id])))
        self._conn.commit()
        self._conn.close()
        self._dirty = set()

    def remove(self, task_id):
        """remove saved dependencies from DB for taskId"""
        if task_id in self._cache:
            del self._cache[task_id]
        if task_id in self._dirty:
            self._dirty.remove(task_id)
        self._conn.execute('delete from doit where task_id=?', (task_id,))

    def remove_all(self):
        """remove saved dependencies from DB for all task"""
        self._conn.execute('delete from doit')
        self._cache = {}
        self._dirty = set()


class FileChangedChecker(object):
    """Base checker for dependencies, must be inherited."""

    CheckerError = os.error

    def exists(self, file_path):
        return os.path.exists(file_path)

    def info(self, file_path):
        return os.stat(file_path)

    def check_modified(self, file_path, file_stat, state):
        """Check if file in file_path is modified from previous "state".

        @param file_path (string): file path
        @param file_stat: result of os.stat() of file_path
        @param state: state that was previously saved with ``get_state()``
        @returns (bool): True if dep is modified

        """
        raise NotImplementedError()

    def get_state(self, dep, current_state):
        """Compute the state of a task after it has been successfully executed.

        @param dep (str): path of the dependency file.
        @param current_state (tuple): the current state, saved from a previous
            execution of the task (None if the task was never run).
        @returns: the new state. Return None if the state is unchanged.

        The parameter `current_state` is passed to allow speed optimization,
        see MD5Checker.get_state().
        """
        raise NotImplementedError()


class MD5Checker(FileChangedChecker):
    """MD5 checker, uses the md5sum.

    This is the default checker used by doit.

    As an optimization the check uses (timestamp, file-size, md5).
    If the timestamp is the same it considers that the file has the same
    content. If file size is different its content certainly is modified.
    Finally the md5 is used for a different timestamp with the same size.
    """

    def check_modified(self, file_path, file_stat, state):
        """Check if file in file_path is modified from previous "state".
        """
        timestamp, size, file_md5 = state

        # 1 - if timestamp is not modified file is the same
        if file_stat.st_mtime == timestamp:
            return False

        # 2 - if size is different file is modified
        if file_stat.st_size != size:
            return True

        # 3 - check md5
        return file_md5 != get_file_md5(file_path)


    def get_state(self, dep, current_state):
        timestamp = os.path.getmtime(dep)
        # time optimization. if dep is already saved with current
        # timestamp skip calculating md5
        if current_state and current_state[0] == timestamp:
            return
        size = os.path.getsize(dep)
        md5 = get_file_md5(dep)
        return timestamp, size, md5


class TimestampChecker(FileChangedChecker):
    """Checker that use only the timestamp."""

    def check_modified(self, file_path, file_stat, state):
        return file_stat.st_mtime != state

    def get_state(self, dep, current_state):
        """@returns float: mtime for file `dep`"""
        return os.path.getmtime(dep)


# name of checkers class available
CHECKERS = {'md5': MD5Checker,
            'timestamp': TimestampChecker}


class DependencyStatus(object):
    """Result object for Dependency.get_status.

    @ivar status: (str) one of "run", "up-to-date" or "error"
    """

    def __init__(self, get_log):
        self.get_log = get_log
        self.status = 'up-to-date'
        # save reason task is not up-to-date
        self.reasons = defaultdict(list)
        self.error_reason = None

    def add_reason(self, reason, arg, status='run'):
        """sets state and append reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = status
        if self.get_log:
            self.reasons[reason].append(arg)
        return not self.get_log

    def set_reason(self, reason, arg):
        """sets state and reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = 'run'
        if self.get_log:
            self.reasons[reason] = arg
        return not self.get_log

    def get_error_message(self):
        '''return str with error message'''
        return self.error_reason


class TaskState:
    """Task state persistence - values, results, ignore status.

    Handles saving and retrieving task execution results including:
    - Task output values (returned by actions)
    - Task result hash (for up-to-date checking)
    - File dependency states
    - Ignore status

    This is a focused extraction from the Dependency class.
    """

    def __init__(self, store, checker):
        """
        @param store: ProcessingStateStore backend for persistence
        @param checker: FileChangedChecker for computing file states
        """
        self.store = store
        self.checker = checker

    def save_success(self, task, result_hash=None):
        """Save info after a task is successfully executed.

        @param task: Task that completed successfully
        @param result_hash: explicitly set result_hash (optional)
        """
        # save task values
        self.store.set(task.name, StorageKey.VALUES, task.values)

        # save task result md5
        if result_hash is not None:
            self.store.set(task.name, StorageKey.RESULT, result_hash)
        elif task.result:
            if isinstance(task.result, dict):
                self.store.set(task.name, StorageKey.RESULT, task.result)
            else:
                self.store.set(task.name, StorageKey.RESULT, get_md5(task.result))

        # file-dep
        self.store.set(task.name, StorageKey.CHECKER, self.checker.__class__.__name__)
        for dep in task.file_dep:
            state = self.checker.get_state(dep, self.store.get(task.name, dep))
            if state is not None:
                self.store.set(task.name, dep, state)

        # save list of file_deps
        self.store.set(task.name, StorageKey.DEPS, tuple(task.file_dep))

    def get_values(self, task_name):
        """Get all saved values from a task.

        @param task_name: name of the task
        @return: dict of task values
        """
        values = self.store.get(task_name, StorageKey.VALUES)
        return values or {}

    def get_value(self, task_id, key_name):
        """Get a specific saved value from task.

        @param task_id: task name
        @param key_name: key in the values dict
        @return: the value
        @raise Exception: if task has no values or key not found
        """
        if not self.store.in_(task_id):
            raise Exception("taskid '%s' has no computed value!" % task_id)
        values = self.get_values(task_id)
        if key_name not in values:
            msg = "Invalid arg name. Task '%s' has no value for '%s'."
            raise Exception(msg % (task_id, key_name))
        return values[key_name]

    def get_result(self, task_name):
        """Get the result saved from a task.

        @return: dict or md5sum
        """
        return self.store.get(task_name, StorageKey.RESULT)

    def remove_success(self, task):
        """Remove saved info from task."""
        self.store.remove(task.name)

    def set_ignore(self, task):
        """Mark task to be ignored."""
        self.store.set(task.name, StorageKey.IGNORE, '1')

    def is_ignored(self, task):
        """Check if task is marked to be ignored."""
        return self.store.get(task.name, StorageKey.IGNORE)

    def has_state(self, task_name):
        """Check if task has any stored state."""
        return self.store.in_(task_name)


class UpToDateChecker:
    """Check if a task needs to run.

    Performs all up-to-date checks including:
    - uptodate callables/values
    - Target existence
    - File dependency changes
    - Checker class changes

    This is a focused extraction from Dependency.get_status().
    """

    def __init__(self, store, checker):
        """
        @param store: ProcessingStateStore backend for state lookup
        @param checker: FileChangedChecker for file state comparison
        """
        self.store = store
        self.checker = checker

    def check(self, task, tasks_dict, get_values_func, get_log=False):
        """Check if task is up to date. Sets task.dep_changed.

        If the checker class changed since the previous run, the task is
        deleted, to be sure that its state is not re-used.

        @param task: Task to check
        @param tasks_dict: dict of all tasks (passed to uptodate callables)
        @param get_values_func: function(task_name) -> dict of values
        @param get_log: if True, adds all reasons to result object
        @return: DependencyStatus with status 'up-to-date', 'run', or 'error'
        """
        result = DependencyStatus(get_log)
        task.dep_changed = []

        # check uptodate bool/callables
        uptodate_result_list = []
        for utd, utd_args, utd_kwargs in task.uptodate:
            # if parameter is a callable
            if hasattr(utd, '__call__'):
                # 1) setup object with global info all tasks
                if isinstance(utd, UptodateCalculator):
                    utd.setup(self, tasks_dict)
                # 2) add magic positional args for `task` and `values`
                spec_args = list(inspect.signature(utd).parameters.keys())
                magic_args = []
                for i, name in enumerate(spec_args):
                    if i == 0 and name == 'task':
                        magic_args.append(task)
                    elif i == 1 and name == 'values':
                        magic_args.append(get_values_func(task.name))
                args = magic_args + utd_args
                # 3) call it and get result
                uptodate_result = utd(*args, **utd_kwargs)
            elif isinstance(utd, str):
                uptodate_result = subprocess.call(
                    utd, shell=True,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL) == 0
            # parameter is a value
            else:
                uptodate_result = utd

            # None means uptodate was not really calculated
            if uptodate_result is None:
                continue
            uptodate_result_list.append(uptodate_result)
            if not uptodate_result:
                result.add_reason(DependencyReason.UPTODATE_FALSE, (utd, utd_args, utd_kwargs))

        # any uptodate check is false
        if not get_log and result.status == 'run':
            return result

        # no dependencies means it is never up to date.
        if not (task.file_dep or uptodate_result_list):
            if result.set_reason(DependencyReason.HAS_NO_DEPENDENCIES, True):
                return result

        # if target file is not there, task is not up to date
        for targ in task.targets:
            if not self.checker.exists(targ):
                task.dep_changed = list(task.file_dep)
                if result.add_reason(DependencyReason.MISSING_TARGET, targ):
                    return result

        # check for modified file_dep checker
        previous = self.store.get(task.name, StorageKey.CHECKER)
        checker_name = self.checker.__class__.__name__
        if previous and previous != checker_name:
            task.dep_changed = list(task.file_dep)
            # remove all saved values otherwise they might be re-used
            self.store.remove(task.name)
            if result.set_reason(DependencyReason.CHECKER_CHANGED, (previous, checker_name)):
                return result

        # check for modified file_dep
        previous = self.store.get(task.name, StorageKey.DEPS)
        previous_set = set(previous) if previous else None
        if previous_set and previous_set != task.file_dep:
            if get_log:
                added_files = sorted(list(task.file_dep - previous_set))
                removed_files = sorted(list(previous_set - task.file_dep))
                result.set_reason(DependencyReason.ADDED_FILE_DEP, added_files)
                result.set_reason(DependencyReason.REMOVED_FILE_DEP, removed_files)
            result.status = 'run'

        # list of file_dep that changed
        check_modified = self.checker.check_modified
        changed = []
        for dep in task.file_dep:
            state = self.store.get(task.name, dep)
            try:
                file_stat = self.checker.info(dep)
            except self.checker.CheckerError:
                error_msg = "Dependent file '{}' does not exist.".format(dep)
                result.error_reason = error_msg.format(dep)
                if result.add_reason(DependencyReason.MISSING_FILE_DEP, dep, 'error'):
                    return result
            else:
                if state is None or check_modified(dep, file_stat, state):
                    changed.append(dep)
        task.dep_changed = changed

        if len(changed) > 0:
            result.set_reason(DependencyReason.CHANGED_FILE_DEP, changed)

        return result



class Dependency(object):
    """Facade for managing task dependencies.

    Combines TaskState (persistence) and UpToDateChecker (status checking)
    into a single interface for backward compatibility with existing code.

    Each dependency is saved in "db". There are several "db" backends.
    It uses a Key-Value format where the key is task-name
    and value is a dictionary.

    :ivar string name: filepath of the DB file
    :ivar bool _closed: DB was flushed to file

    Usage:
        # File-based storage (traditional usage with factory pattern)
        dep = Dependency(DbmDB, '/path/to/db')

        # With a pre-configured backend instance
        backend = InMemoryStateStore()
        dep = Dependency(backend)

        # With custom checker
        dep = Dependency(backend, checker_cls=TimestampChecker)
    """
    def __init__(self, backend_or_class, backend_name=None, checker_cls=None,
                 codec_cls=JSONCodec, module_name=None):
        """Initialize the dependency manager.

        @param backend_or_class: Either a ProcessingStateStore instance, or a
            class (like DbmDB, JsonDB, SqliteDB) that will be instantiated.
        @param backend_name: Path to the database file. Required if
            backend_or_class is a class, ignored if it's an instance.
        @param checker_cls: FileChangedChecker class to use (MD5Checker or
            TimestampChecker). Defaults to MD5Checker for file-based backends,
            TimestampChecker for InMemoryStateStore.
        @param codec_cls: Codec class for serialization (default: JSONCodec)
        @param module_name: DBM module name (for DbmDB backend only)
        """
        self._closed = False

        # Determine if we received an instance or a class
        if isinstance(backend_or_class, ProcessingStateStore):
            # Received a pre-configured instance
            self.backend = backend_or_class
            self.db_class = type(backend_or_class)

            # For in-memory storage, default to TimestampChecker (Makefile-style).
            if checker_cls is None:
                if isinstance(backend_or_class, InMemoryStateStore):
                    checker_cls = TimestampChecker
                else:
                    checker_cls = MD5Checker
        else:
            # Received a class - need to instantiate it
            if backend_name is None:
                raise ValueError(
                    "backend_name is required when passing a backend class. "
                    "Either pass a ProcessingStateStore instance, or pass a "
                    "class with a backend_name path."
                )
            self.db_class = backend_or_class
            self.backend = backend_or_class(
                backend_name, codec=codec_cls(), module_name=module_name
            )
            # File-based storage defaults to MD5Checker for accurate change detection
            if checker_cls is None:
                checker_cls = MD5Checker

        self._checker = checker_cls()

        # Create the focused components
        self._task_state = TaskState(self.backend, self._checker)
        self._uptodate_checker = UpToDateChecker(self.backend, self._checker)

        # Expose low-level backend access for backward compatibility
        self._set = self.backend.set
        self._get = self.backend.get
        self.remove = self.backend.remove
        self.remove_all = self.backend.remove_all
        self._in = self.backend.in_
        self.name = self.backend.name

    @property
    def checker(self):
        """Get the file change checker."""
        return self._checker

    @checker.setter
    def checker(self, value):
        """Set the file change checker and update internal components."""
        self._checker = value
        self._task_state.checker = value
        self._uptodate_checker.checker = value

    def close(self):
        """Write DB in file"""
        if not self._closed:
            self.backend.dump()
            self._closed = True

    # --- Delegate to TaskState ---

    def save_success(self, task, result_hash=None):
        """Save info after a task is successfully executed."""
        return self._task_state.save_success(task, result_hash)

    def get_values(self, task_name):
        """Get all saved values from a task."""
        return self._task_state.get_values(task_name)

    def get_value(self, task_id, key_name):
        """Get saved value from task."""
        return self._task_state.get_value(task_id, key_name)

    def get_result(self, task_name):
        """Get the result saved from a task."""
        return self._task_state.get_result(task_name)

    def remove_success(self, task):
        """Remove saved info from task."""
        return self._task_state.remove_success(task)

    def ignore(self, task):
        """Mark task to be ignored."""
        return self._task_state.set_ignore(task)

    def status_is_ignore(self, task):
        """Check if task is marked to be ignored."""
        return self._task_state.is_ignored(task)

    # --- Delegate to UpToDateChecker ---

    def get_status(self, task, tasks_dict, get_log=False):
        """Check if task is up to date. Sets task.dep_changed.

        @param task: (Task)
        @param tasks_dict: (dict: Task) passed to objects used on uptodate
        @param get_log: (bool) if True, adds all reasons to the return object
        @return: (DependencyStatus) with status 'up-to-date', 'run', or 'error'
        """
        return self._uptodate_checker.check(
            task, tasks_dict, self.get_values, get_log
        )



#############

class UptodateCalculator(object):
    """Base class for 'uptodate' that need access to all tasks
    """
    def __init__(self):
        self.get_val = None  # store.get function
        self.tasks_dict = None  # dict with all tasks

    def setup(self, checker_or_dep_manager, tasks_dict):
        """Setup calculator with access to state and tasks.

        @param checker_or_dep_manager: UpToDateChecker or Dependency instance
        @param tasks_dict: dict of all tasks
        """
        # Support both UpToDateChecker (new) and Dependency (backward compat)
        if hasattr(checker_or_dep_manager, 'store'):
            self.get_val = checker_or_dep_manager.store.get
        else:
            self.get_val = checker_or_dep_manager._get
        self.tasks_dict = tasks_dict


if __name__ == '__main__':
    # inspect available DBM modules and used extensions
    import tempfile
    from pathlib import Path
    import os

    for name in dbm._names:
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f'# {name}')
            try:
                mod = __import__(name, fromlist=['open'])
            except ImportError:
                print('NOT FOUND')
                continue
            db = mod.open(f'{tmpdir}/test', 'c')
            db['foo'] = 'bar'
            db.close()

            for file in Path(tmpdir).iterdir():
                print(file.name)
