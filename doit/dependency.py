"""Manage (save/check) task dependency-on-files data."""

import os
import hashlib
import dumbdbm
import anydbm as ddbm

# uncomment imports below to run tests on all dbm backends...
#import dbhash as ddbm # ok (removed from python3)
#import dumbdbm as ddbm # test_corrupted_file fails
#import dbm as ddbm # test_corrupted_file fails
#import gdbm as ddbm # ok <= TODO make this the default

#FIXME move json import to __init__.py
# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json


USE_FILE_TIMESTAMP = True


def get_md5(input_data):
    """return md5 from string or unicode"""
    if isinstance(input_data, unicode):
        byte_data = input_data.encode("utf-8")
    else:
        byte_data = input_data
    return hashlib.md5(byte_data).hexdigest()

def md5sum(path):
    """Calculate the md5 sum from file content.

    @param path: (string) file path
    @return: (string) md5
    """
    file_data = open(path,'rb')
    result = get_md5(file_data.read())
    file_data.close()
    return result


def check_modified(file_path, state):
    """check if file in file_path is modified from previous "state"
    @param file_path (string): file path
    @param state (tuple), timestamp, size, md5
    @returns (bool):
    """
    if state is None:
        return True

    timestamp, size, file_md5 = state
    # 1 - if timestamp is not modified file is the same
    if USE_FILE_TIMESTAMP and os.path.getmtime(file_path) == timestamp:
        return False
    # 2 - if size is different file is modified
    if os.path.getsize(file_path) != size:
        return True
    # 3 - check md5
    return file_md5 != md5sum(file_path)


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
            except ValueError, error:
                # file contains corrupted json data
                msg = (error.args[0] +
                       "\nInvalid JSON data in %s\n" %
                       os.path.abspath(self.name) +
                       "To fix this problem, you can just remove the " +
                       "corrupted file, a new one will be generated.\n")
                error.args = (msg,)
                raise
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

    def __init__(self, name):
        """Open/create a DB file"""
        self.name = name
        try:
            self._dbm = ddbm.open(self.name, 'c')
        except ddbm.error, exception:
            message = str(exception)
            if message == 'db type could not be determined':
                # When a corrupted/old format database is found
                # suggest the user to just remove the file
                new_message = (
                    'Dependencies file in %(filename)s seems to use '
                    'an old format or is corrupted.\n'
                    'To fix the issue you can just remove the database file(s) '
                    'and a new one will be generated.'
                    % {'filename': repr(self.name)})
                raise ddbm.error, new_message
            else:
                # Re-raise any other exceptions
                raise

        self._db = {}
        self.dirty = set()

    def dump(self):
        """save/close DBM file"""
        for task_id in self.dirty:
            self._dbm[task_id] = json.dumps(self._db[task_id])
        self._dbm.close()

    def set(self, task_id, dependency, value):
        """Store value in the DB."""
        if task_id not in self._db:
            self._db[task_id] = {}
        self._db[task_id][dependency] = value
        self.dirty.add(task_id)


    def get(self, task_id, dependency):
        """Get value stored in the DB.

        @return: (string) or (None) if entry not found
        """
        # optimization. check this after reduce call count
        if task_id in self._db:
            return self._db[task_id].get(dependency, None)

        if task_id not in self._db and task_id in self._dbm:
            self._db[task_id] = json.loads(self._dbm[task_id])
        if task_id in self._db:
            return self._db[task_id].get(dependency, None)


    def in_(self, task_id):
        """@return bool if task_id is in DB"""
        return task_id in self._dbm or task_id in self.dirty


    def remove(self, task_id):
        """remove saved dependecies from DB for taskId"""
        if task_id in self._db:
            del self._db[task_id]
        if task_id in self._dbm:
            del self._dbm[task_id]
        if task_id in self.dirty:
            self.dirty.remove(task_id)

    def remove_all(self):
        """remove saved dependecies from DB for all tasks"""
        self._db = {}
        # dumb dbm always opens file in update mode
        if isinstance(self._dbm, dumbdbm._Database):
            self._dbm._index = {}
            self._dbm.close()
        self._dbm = ddbm.open(self.name, 'n')
        self.dirty = set()



class DependencyBase(object):
    """Manage tasks dependencies (abstract class)

    Each dependency is a saved in "db". the "db" can have json or dbm
    format where there is a dictionary for every task. each task has a
    dictionary where key is a dependency (abs file path), and the value is the
    dependency signature.
    Apart from dependencies onther values are also saved on the task dictionary
     * 'result:', 'run-once:', 'task:<task-name>', 'ignore:'
     * user(task) defined values are defined in '_values_:' sub-dict

    @ivar name: (string) filepath of the DB file
    @ivar _closed: (bool) DB was flushed to file
    """

    def __init__(self, backend):
        self._closed = False
        self.backend = backend
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

    def save_success(self, task):
        """save info after a task is successfuly executed"""
        # save task values
        self._set(task.name, "_values_:", task.values)

        # save task result md5
        if task.result:
            self._set(task.name, "result:", get_md5(task.result))

        # run-once
        if task.run_once:
            # string value could be anything
            self._set(task.name, 'run-once:', '1')

        # file-dep
        for dep in task.file_dep:
            timestamp = os.path.getmtime(dep)
            # time optimization. if dep is already saved with current timestamp
            # skip calculating md5
            current = self._get(task.name, dep)
            if current and current[0] == timestamp:
                continue
            size = os.path.getsize(dep)
            self._set(task.name, dep, (timestamp, size, md5sum(dep)))

        # result-dep
        for dep in task.result_dep:
            result = self._get(dep, "result:")
            if result is not None:
                self._set(task.name, "task:" + dep, result)


    def get_values(self, task_name):
        """get all saved values from a task"""
        return self._get(task_name, '_values_:')

    def get_value(self, name):
        """get saved value from task
        @param name (str): taskid.argument-name
        """
        parts = name.split('.')
        assert len(parts) == 2
        taskid, arg_name = parts
        if not self._in(taskid):
            raise Exception("taskid '%s' has no computed value!" % taskid)
        values = self.get_values(taskid)
        if arg_name not in values:
            msg = "Invalid arg name. Task '%s' has no value for '%s'."
            raise Exception(msg % (taskid, arg_name))
        return values[arg_name]

    def remove_success(self, task):
        """remove saved info from task"""
        self.remove(task.name)

    def ignore(self, task):
        """mark task to be ignored"""
        self._set(task.name, 'ignore:', '1')


    def get_status(self, task):
        """Check if task is up to date. set task.dep_changed

        @param task: (Task)
        @return: (str) one of up-to-date, ignore, run

        task.dep_changed (list-strings): file-dependencies that are not
        up-to-date if task not up-to-date because of a target, returned value
        will contain all file-dependencies reagrdless they are up-to-date
        or not.
        """
        if self._get(task.name, "ignore:"):
            return 'ignore'

        task.dep_changed = []

        # check uptodate bool/callables
        checked_uptodate = False
        for uptodate in task.uptodate:
            # None means uptodate was not really calculated and should be
            # just ignored
            if uptodate is None:
                continue
            if uptodate:
                checked_uptodate = True
            else:
                return 'run'

        # no dependencies means it is never up to date.
        if ((not task.file_dep) and (not task.result_dep)
            and (not task.run_once) and (not checked_uptodate)):
            return 'run'

        # user managed dependency not up-to-date if it doesnt exist
        if task.run_once and not self._get(task.name, 'run-once:'):
            return 'run'

        # if target file is not there, task is not up to date
        for targ in task.targets:
            if not os.path.exists(targ):
                task.dep_changed = list(task.file_dep)
                return 'run'

        # check for modified dependencies
        changed = []
        status = 'up-to-date' # initial assumption
        for dep in tuple(task.file_dep):
            if not os.path.exists(dep):
                raise Exception("Dependent file '%s' does not exist." % dep)
            if check_modified(dep, self._get(task.name, dep)):
                changed.append(dep)
                status = 'run'

        for dep in tuple(task.result_dep):
            result = self._get(dep, "result:")
            if ((result is None) or
                (self._get(task.name,"task:" + dep) != result)):
                status = 'run'
                break

        task.dep_changed = changed #FIXME create a separate function for this
        return status


class JsonDependency(DependencyBase):
    """Task dependency manager with JSON backend"""
    def __init__(self, name):
        DependencyBase.__init__(self, JsonDB(name))

class DbmDependency(DependencyBase):
    """Task dependency manager with DBM backend"""
    def __init__(self, name):
        DependencyBase.__init__(self, DbmDB(name))

Dependency = DbmDependency
