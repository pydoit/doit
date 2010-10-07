
"""Manage (save/check) task dependency-on-files data."""

import os
import anydbm

# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json


############ md5
def get_md5_py5(input_data):
    """return md5 from string (python 2.5 and above)"""
    return hashlib.md5(input_data).hexdigest()

def get_md5_py4(input_data): # pragma: no cover
    """return md5 from string"""
    out = md5.new()
    out.update(input_data)
    return out.hexdigest()

## use different md5 libraries depending on python version
get_md5 = None # function return md5 from a string
try:
    import hashlib
    get_md5 = get_md5_py5
# support python 2.4
except ImportError: # pragma: no cover
    import md5
    get_md5 = get_md5_py4
#########################################################



USE_FILE_TIMESTAMP = True

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


class DBM_DB(object):
    """Backend using a DBM file with individual values encoded in JSON"""
    def __init__(self, name):
        """Open/create a DB file"""
        self.name = name
        self._dbm = anydbm.open(self.name, 'c')
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
        return task_id in self._db


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
        self._dbm = anydbm.open(self.name, 'n')
        self.dirty = set()



class DependencyBase(object):
    """Manage tasks dependencies (abstract class)

    Each dependency is a saved in "db". the "db" is a text file using json
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
        # no dependencies means it is never up to date.
        if ((not task.file_dep) and (not task.result_dep)
            and (not task.run_once)):
            return 'run'

        if task.run_always:
            return 'run'

        # user managed dependency not up-to-date if it doesnt exist
        if task.run_once and not self._get(task.name, 'run-once:'):
            return 'run'

        # if target file is not there, task is not up to date
        for targ in task.targets:
            if not os.path.exists(targ):
                task.dep_changed = task.file_dep[:]
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

class DBM_Dependency(DependencyBase):
    """Task dependency manager with DBM backend"""
    def __init__(self, name):
        DependencyBase.__init__(self, DBM_DB(name))

# default "Dependency" implementation to be used
Dependency = DBM_Dependency
