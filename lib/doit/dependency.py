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

def resultmd5sum(value):
    return get_md5(value)


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


    def save(self, taskId, dependency):
        """Save/update dependency on the DB.

        this method will calculate the value to be stored using md5 and then
        call the _set method.
        """
        self._set(taskId,dependency,md5sum(dependency))

    def resultsave(self, taskId, dependency):
        """Save/update dependency on the DB.

        this method will calculate the value to be stored using md5 and then
        call the _set method.
        """
        self._set(taskId,"task:" + dependency,self._get(dependency, "value"))


    def remove(self, taskId):
        """remove saved dependecies from DB for taskId"""
        if taskId in self._db:
            del self._db[taskId]


    def remove_value(self, taskId):
        if taskId in self._db:
            del self._db[taskId]["value"]


    def remove_all(self):
        """remove saved dependecies from DB for all tasks"""
        self._db = {}

    def modified(self, taskId, dependency):
        """Check if dependency for task was modified.

        @return: (boolean)
        """
        return self._get(taskId,dependency) != md5sum(dependency)

    def resultmodified(self, taskId, dependency):
        """Check if dependency for task was modified.

        @return: (boolean)
        """
        return self._get(taskId, "task:" + dependency) != self._get(dependency, "value")


    def close(self):
        """Write DB in file"""
        if not self._closed:
            try:
                fp = open(self.name,'w')
                json.dump(self._db, fp)
            finally:
                fp.close()
            self._closed = True


    def save_dependencies(self,taskId,dependencies):
        """Save dependencies value.

        @param taskId: (string)
        @param dependencies: (list of string)
        """
        # list of files
        for dep in dependencies:
            self.save(taskId,dep)



    def save_resultdependencies(self,taskId,dependencies):
        """Save dependencies value.

        @param taskId: (string)
        @param dependencies: (list of string)
        """
        # list of files
        for dep in dependencies:
            self.resultsave(taskId, dep)


    def save_result(self, taskId, value):
        self._set(taskId,"value",resultmd5sum(value))


    def save_run_once(self,taskId):
        """Save run_once task as executed"""
        self._set(taskId,'','1')# string could be any value


    def up_to_date(self, taskId, dependencies, targets, runOnce, result_dep):
        """Check if task is up to date.

        @param taskId: (string)
        @param dependencies: (list of string)
        @param runOnce: (bool) task has dependencies but they are not managed
        by doit. they can only be cleared manualy.
        @return: (bool, changed) True if up to date, False needs to re-execute.
            changed (list-strings): file-dependencies that are not up-to-date
            if task not up-to-date because of a target, returned value
            will contain all file-dependencies reagrdless they are up-to-date
            or not.
        """

        # no dependencies means it is never up to date.
        if (not dependencies) and (not runOnce) and (not result_dep):
            return False, []

        # user managed dependency always up-to-date if it exists
        if runOnce and not self._get(taskId,''):
            return False, []

        # if target file is not there, task is not up to date
        for targ in targets:
            if not os.path.exists(targ):
                return False, dependencies

        # check for modified dependencies
        changed = []
        buptod = True
        for dep in tuple(dependencies):
            if self.modified(taskId,dep):
                changed.append(dep)
                buptod = False

        for dep in tuple(result_dep):
            if self.resultmodified(taskId, dep):
                buptod = False

        return buptod, changed
