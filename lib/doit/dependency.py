
"""Manage (save/check) task dependency-on-files data."""

import os

# Use Python 2.6 json or simplejson
try:
    import json
    json # keep pyflakes quiet
except ImportError:
    import simplejson as json


## use different md5 libraries depending on python version
get_md5 = None # function return md5 from a string
try:
    import hashlib
    def get_md5_py5(input):
        return hashlib.md5(input).hexdigest()
    get_md5 = get_md5_py5
# support python 2.4
except ImportError:
    import md5
    def get_md5_py4(input):
        out = md5.new()
        out.update(input)
        return out.hexdigest()
    get_md5 = get_md5_py4


def md5sum(path):
    """Calculate the md5 sum from file content.

    @param path: (string) file path
    @return: (string) md5
    """
    f = open(path,'rb')
    result = get_md5(f.read())
    f.close()
    return result



class Dependency(object):
    """Manage dependency on files.

    Each dependency is a saved in "db". the "db" is a text file using json
    format where there is a dictionary for every task. each task has a
    dictionary where key is  dependency (abs file path), and the value is the
    dependency signature.
    In case dependency is a bool value True it will be saved with key: ""
    value: True.
    """

    def __init__(self, name, new=False):
        """Open/create a DB file.

        @param name: (string) filepath of the DB file
        @param new: (boolean) always create a new empty database
        """
        self.name = name
        self._closed = False

        if new or not os.path.exists(self.name):
            self._db = {}
        else:
            try:
                fp = open(self.name,'r')
                self._db = json.load(fp)
            finally:
                fp.close()


    def _set(self, taskId, dependency, value):
        """Store value in the DB."""
        if taskId not in self._db:
            self._db[taskId] = {}
        self._db[taskId][dependency] = value


    def _get(self, taskId, dependency):
        """Get value stored in the DB.

        @return: (string) or (None) if entry not found
        """
        if taskId in self._db:
            return self._db[taskId].get(dependency, None)


    def remove(self, taskId):
        """remove saved dependecies from DB for taskId"""
        if taskId in self._db:
            del self._db[taskId]


    def remove_all(self):
        """remove saved dependecies from DB for all tasks"""
        self._db = {}


    def close(self):
        """Write DB in file"""
        if not self._closed:
            try:
                fp = open(self.name,'w')
                json.dump(self._db, fp)
            finally:
                fp.close()
            self._closed = True


    ####### task specific

    def save_success(self, task):
        """save info after a task is successfuly executed"""
        # save task values
        for key, value in task.values.iteritems():
            self._set(task.name, (":%s:" % key), value)

        # save task result md5
        if task.result:
            self._set(task.name, "result:", get_md5(task.result))

        # run-once
        if task.run_once:
            self._set(task.name,'run-once:','1')# string could be any value

        # file-dep
        for dep in task.file_dep:
            self._set(task.name, dep, md5sum(dep))

        # result-dep
        for dep in task.result_dep:
            result = self._get(dep, "result:")
            if result is not None:
                self._set(task.name, "task:" + dep, result)


    def remove_success(self, task):
        """remove saved info from task"""
        if task.name in self._db:
            del self._db[task.name]


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
            if self._get(task.name, dep) != md5sum(dep):
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
