"""Manage (save/check) task dependency-on-files data."""

import os
import hashlib
import subprocess
import inspect
import six
if six.PY3: # pragma: no cover
    from dbm import dumb
    import dbm as ddbm
else:
    import dumbdbm as dumb
    import anydbm as ddbm

# uncomment imports below to run tests on all dbm backends...
#import dbhash as ddbm # (removed from python3)
#import dumbdbm as ddbm
#import dbm as ddbm
#import gdbm as ddbm

# note: to check which DBM backend is being used:
#       >>> anydbm._defaultmod

import json
import sqlite3


class DatabaseException(Exception):
    """Exception class for whatever backend exception"""
    pass


class DependencyException(Exception):
    """Exception class for whatever backend exception"""
    pass


def get_md5(input_data):
    """return md5 from string or unicode"""
    if isinstance(input_data, six.text_type):
        byte_data = input_data.encode("utf-8")
    else:
        byte_data = input_data
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


class JsonDB(object):
    """Backend using a single text file with JSON content"""

    def __init__(self, name):
        """Open/create a DB file"""
        self.name = name
        if not os.path.exists(self.name):
            self._db = {}
        else:
            self._db = self._load()

    def _load(self):
        """load db content from file"""
        db_file = open(self.name, 'r')
        try:
            try:
                return json.load(db_file)
            except ValueError as error:
                # file contains corrupted json data
                msg = (error.args[0] +
                       "\nInvalid JSON data in %s\n" %
                       os.path.abspath(self.name) +
                       "To fix this problem, you can just remove the " +
                       "corrupted file, a new one will be generated.\n")
                error.args = (msg,)
                raise DatabaseException(msg)
        finally:
            db_file.close()

    def dump(self):
        """save DB content in file"""
        try:
            db_file = open(self.name, 'w')
            json.dump(self._db, db_file)
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
        """remove saved dependecies from DB for taskId"""
        if task_id in self._db:
            del self._db[task_id]

    def remove_all(self):
        """remove saved dependecies from DB for all tasks"""
        self._db = {}



def encode_task_id(func):
    """in python 2 dbm module does not automatically convert unicode to bytes"""
    if not six.PY3:
        def wrap(self, key, *args):
            if isinstance(key, six.text_type):
                key = key.encode('utf-8')
            return func(self, key, *args)
        return wrap
    else:  # pragma: no cover
        return func


class DbmDB(object):
    """Backend using a DBM file with individual values encoded in JSON

    On initialization all items are read from DBM file and loaded on _dbm.
    During execution whenever an item is read ('get' method) the json value
    is cached on _db. If a item is modified _db is update and the id is added
    to the 'dirty' set. Only on 'dump' all dirty items values are encoded
    in json into _dbm and the DBM file is saved.

    @ivar name: (str) file name/path
    @ivar _dbm: (dbm) items with json encoded values
    @ivar _db: (dict) items with python-dict as value
    @ivar dirty: (set) id of modified tasks
    """
    DBM_CONTENT_ERROR_MSG = 'db type could not be determined'

    def __init__(self, name):
        """Open/create a DB file"""
        self.name = name
        try:
            self._dbm = ddbm.open(self.name, 'c')
        except ddbm.error as exception:
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
            self._dbm[task_id] = json.dumps(self._db[task_id])
        self._dbm.close()


    @encode_task_id
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

         python3: when for get/set key is convert to bytes but not for 'in'
        """
        return key.encode('utf-8') in self._dbm


    @encode_task_id
    def get(self, task_id, dependency):
        """Get value stored in the DB.

        @return: (string) or (None) if entry not found
        """
        # optimization, just try to get it without checking it exists
        if task_id in self._db:
            return self._db[task_id].get(dependency, None)
        else:
            try:
                task_data = self._dbm[task_id]
            except KeyError:
                return
            self._db[task_id] = json.loads(task_data.decode('utf-8'))
            return self._db[task_id].get(dependency, None)


    @encode_task_id
    def in_(self, task_id):
        """@return bool if task_id is in DB"""
        return self._in_dbm(task_id) or task_id in self.dirty


    @encode_task_id
    def remove(self, task_id):
        """remove saved dependecies from DB for taskId"""
        if task_id in self._db:
            del self._db[task_id]
        if self._in_dbm(task_id):
            del self._dbm[task_id]
        if task_id in self.dirty:
            self.dirty.remove(task_id)


    def remove_all(self):
        """remove saved dependecies from DB for all tasks"""
        self._db = {}
        # dumb dbm always opens file in update mode
        if isinstance(self._dbm, dumb._Database): # pragma: no cover
            self._dbm._index = {}
            self._dbm.close()
        # gdbm can not be running on 2 instances on same thread
        # see https://bitbucket.org/schettino72/doit/issue/16/
        del self._dbm
        self._dbm = ddbm.open(self.name, 'n')
        self.dirty = set()



class SqliteDB(object):
    """ sqlite3 json backend """

    def __init__(self, name):
        self.name = name
        self._conn = self._sqlite3(self.name)

    @staticmethod
    def _sqlite3(name):
        """Open/create a sqlite3 DB file"""
        def dict_factory(cursor, row):
            """convert row to dict"""
            data = {}
            for idx, col in enumerate(cursor.description):
                data[col[0]] = row[idx]
            return data
        def converter(data):
            return json.loads(data.decode('utf-8'))

        sqlite3.register_adapter(list, json.dumps)
        sqlite3.register_adapter(dict, json.dumps)
        sqlite3.register_converter("json", converter)
        conn = sqlite3.connect(
            name,
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
            isolation_level=None)
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
        data = self._get_task_data(task_id)
        return data.get(dependency, None)

    def _get_task_data(self, task_id):
        data = self._conn.execute('select task_data from doit where task_id=?',
                                  (task_id,)).fetchone()
        return data['task_data'] if data else {}

    def set(self, task_id, dependency, value):
        """Store value in the DB."""
        task_data = self._get_task_data(task_id)
        task_data[dependency] = value
        self._conn.execute('insert or replace into doit values (?,?)',
                           (task_id, task_data))

    def in_(self, task_id):
        if self._conn.execute('select task_id from doit where task_id=?',
                              (task_id,)).fetchone():
            return True
        return False

    def dump(self):
        """save/close sqlite3 DB file"""
        self._conn.commit()
        self._conn.close()

    def remove(self, task_id):
        """remove saved dependecies from DB for taskId"""
        self._conn.execute('delete from doit where task_id=?', (task_id,))

    def remove_all(self):
        """remove saved dependecies from DB for all task"""
        self._conn.execute('delete from doit')


class FileChangedChecker(object):
    """Base checker for dependencies, must be inherited."""

    def check_modified(self, file_path, file_stat, state):
        """Check if file in file_path is modified from previous "state".

        @param file_path (string): file path
        @param file_stat: result of os.stat() of file_path
        @param state: state that was previously saved with ``get_state()``
        @returns (bool): True if dep is modified

        """
        raise NotImplementedError()

    def get_state(self, dep, current_state):
        """Compute the state of a task after it has been successfuly executed.

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


class DependencyBase(object):
    """Manage tasks dependencies (abstract class)

    Each dependency is saved in "db". the "db" can have json or dbm
    format where there is a dictionary for every task. each task has a
    dictionary where key is a dependency (abs file path), and the value is the
    dependency signature.
    Apart from dependencies other values are also saved on the task dictionary
     * 'result:', 'task:<task-name>', 'ignore:'
     * user(task) defined values are defined in '_values_:' sub-dict

    @ivar name: (string) filepath of the DB file
    @ivar _closed: (bool) DB was flushed to file
    """

    DB_CLASS = None  # a class with DB interface (i.e. JsonDB, DbmDB, ...)

    def __init__(self, backend_name, checker_cls=MD5Checker):
        self._closed = False
        self.checker = checker_cls()
        self.backend = self.DB_CLASS(backend_name)
        self._set = self.backend.set
        self._get = self.backend.get
        self.remove = self.backend.remove
        self.remove_all = self.backend.remove_all
        self._in = self.backend.in_
        self.name = self.backend.name

    def close(self):
        """Write DB in file"""
        if not self._closed:
            self.backend.dump()
            self._closed = True


    ####### task specific

    def save_success(self, task, result_hash=None):
        """save info after a task is successfuly executed

        :param result_hash: (str) explicitly set result_hash
        """
        # save task values
        self._set(task.name, "_values_:", task.values)

        # save task result md5
        if result_hash is not None:
            self._set(task.name, "result:", result_hash)
        elif task.result:
            if isinstance(task.result, dict):
                self._set(task.name, "result:", task.result)
            else:
                self._set(task.name, "result:", get_md5(task.result))

        # file-dep
        self._set(task.name, 'checker:', self.checker.__class__.__name__)
        for dep in task.file_dep:
            state = self.checker.get_state(dep, self._get(task.name, dep))
            if state is not None:
                self._set(task.name, dep, state)

        # save list of file_deps
        self._set(task.name, 'deps:', tuple(task.file_dep))

    def get_values(self, task_name):
        """get all saved values from a task
        @return dict
        """
        values = self._get(task_name, '_values_:')
        return values or {}

    def get_value(self, task_id, key_name):
        """get saved value from task
        @param task_id (str)
        @param key_name (str): key result dict of the value
        """
        if not self._in(task_id):
            # FIXME do not use generic exception
            raise Exception("taskid '%s' has no computed value!" % task_id)
        values = self.get_values(task_id)
        if key_name not in values:
            msg = "Invalid arg name. Task '%s' has no value for '%s'."
            raise Exception(msg % (task_id, key_name))
        return values[key_name]

    def get_result(self, task_name):
        """get the result saved from a task
        @return dict or md5sum
        """
        return self._get(task_name, 'result:')

    def remove_success(self, task):
        """remove saved info from task"""
        self.remove(task.name)

    def ignore(self, task):
        """mark task to be ignored"""
        self._set(task.name, 'ignore:', '1')

    def status_is_ignore(self, task):
        """check if task is marked to be ignored"""
        return self._get(task.name, "ignore:")

    # TODO add option to log this
    def get_status(self, task, tasks_dict):
        """Check if task is up to date. set task.dep_changed

        If the checker class changed since the previous run, the task is
        deleted, to be sure that its state is not re-used.

        @param task: (Task)
        @param tasks_dict: (dict: Task) passed to objects used on uptodate
        @return: (str) one of up-to-date, run

        task.dep_changed (list-strings): file-dependencies that are not
        up-to-date if task not up-to-date because of a target, returned value
        will contain all file-dependencies reagrdless they are up-to-date
        or not.
        """
        task.dep_changed = []

        # check uptodate bool/callables
        checked_uptodate = False
        for utd, utd_args, utd_kwargs in task.uptodate:
            # if parameter is a callable
            if hasattr(utd, '__call__'):
                # FIXME control verbosity, check error messages
                # 1) setup object with global info all tasks
                if isinstance(utd, UptodateCalculator):
                    utd.setup(self, tasks_dict)
                # 2) add magic positional args for `task` and `values`
                # if present.
                # get args removing self if present
                if inspect.isfunction(utd):
                    spec_args = inspect.getargspec(utd).args
                elif inspect.ismethod(utd):
                    spec_args = inspect.getargspec(utd).args[1:]
                else:
                    spec_args = inspect.getargspec(utd.__call__).args[1:]
                magic_args = []
                for i, name in enumerate(spec_args):
                    if i == 0 and name == 'task':
                        magic_args.append(task)
                    elif i == 1 and name == 'values':
                        magic_args.append(self.get_values(task.name))
                args = magic_args + utd_args
                # 3) call it and get result
                uptodate_result = utd(*args, **utd_kwargs)
            elif isinstance(utd, six.string_types):
                # TODO py3.3 has subprocess.DEVNULL
                with open(os.devnull, 'wb') as null:
                    uptodate_result = subprocess.call(
                        utd, shell=True, stderr=null, stdout=null) == 0
            # parameter is a value
            else:
                uptodate_result = utd

            # None means uptodate was not really calculated and should be
            # just ignored
            if uptodate_result is None:
                continue
            if uptodate_result:
                checked_uptodate = True
            else:
                return 'run'

        # no dependencies means it is never up to date.
        if not (task.file_dep or checked_uptodate):
            return 'run'

        # if target file is not there, task is not up to date
        for targ in task.targets:
            if not os.path.exists(targ):
                task.dep_changed = list(task.file_dep)
                return 'run'

        # check for modified file_dep checker
        previous = self._get(task.name, 'checker:')
        if previous and previous != self.checker.__class__.__name__:
            task.dep_changed = list(task.file_dep)
            # remove all saved values otherwise they might be re-used by
            # some optmization on MD5Checker.get_state()
            self.remove(task.name)
            return 'run'

        # check for modified file_dep
        previous = self._get(task.name, 'deps:')
        if previous and set(previous) != task.file_dep:
            status = 'run'
        else:
            status = 'up-to-date'  # initial assumption

        # list of file_dep that changed
        check_modified = self.checker.check_modified
        changed = []
        for dep in task.file_dep:
            state = self._get(task.name, dep)
            try:
                file_stat = os.stat(dep)
            except OSError:
                raise DependencyException("Dependent file '{}' does not exist."
                                          .format(dep))
            if state is None or check_modified(dep, file_stat, state):
                changed.append(dep)
        if len(changed) > 0:
            status = 'run'

        task.dep_changed = changed  # FIXME create a separate function for this
        return status


####################

class JsonDependency(DependencyBase):
    """Task dependency manager with JSON backend"""
    DB_CLASS = JsonDB


class DbmDependency(DependencyBase):
    """Task dependency manager with DBM backend"""
    DB_CLASS = DbmDB


class SqliteDependency(DependencyBase):
    """Task dependency manager with sqlite backend"""
    DB_CLASS = SqliteDB

# map string used in cmdline option to class
backend_map = {
    'json': JsonDependency,
    'dbm': DbmDependency,
    'sqlite3': SqliteDependency,
}

#############

class UptodateCalculator(object):
    """Base class for 'uptodate' that need access to all tasks
    """
    def __init__(self):
        self.get_val = None # Dependency._get
        self.tasks_dict = None # dict with all tasks

    def setup(self, dep_manager, tasks_dict):
        """@param"""
        self.get_val = dep_manager._get
        self.tasks_dict = tasks_dict


# defaut dependency backend implementation
Dependency = DbmDependency
