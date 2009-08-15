"""Manage (save/check) task dependency-on-files data."""

import os
import anydbm

from doit.util import md5sum

class Dependency(object):
    """Manage dependency on files.

    Each dependency is a saved in dbm. where the key is taskId + dependency
    (abs file path), and the value is the dependency signature.

    In case dependency is a bool value True it will be saved with key: taskId
    value: True.
    """

    def __init__(self, name, new=False):
        """Open/create a DBM file.

        @param name: (string) filepath of the DBM file
        @param new: (boolean) always create a new empty database
        """
        self.name = name
        self._closed = False
        if new:
            self._db = anydbm.open(name,'n')
        else:
            self._db = anydbm.open(name,'c')


    def __del__(self):
        self.close()

    def _set(self, taskId, dependency, value):
        """Store value in the DBM."""
        self._db[taskId+dependency] = value

    def _get(self, taskId, dependency):
        """Get value stored in the DBM.

        @return: (string) or (None) if entry not found
        """
        return self._db.get(taskId+dependency,None)

    def save(self, taskId, dependency):
        """Save/update dependency on the DB.

        this method will calculate the value to be stored using md5 and then
        call the _set method.
        """
        self._set(taskId,dependency,md5sum(dependency))

    def modified(self,taskId, dependency):
        """Check if dependency for task was modified.

        @return: (boolean)
        """
        return self._get(taskId,dependency) != md5sum(dependency)

    def close(self):
        """Close DBM file. Flush changes."""
        if not self._closed:
            self._db.close()
            self._closed = True

    def save_dependencies(self,taskId,dependencies):
        """Save dependencies value.

        @param taskId: (string)
        @param dependencies: (list of string)
        """
        # list of files
        for dep in dependencies:
            self.save(taskId,dep)

    def save_run_once(self,taskId):
        """Save run_once task as executed"""
        self._set(taskId,'','1')# string could be any value

    def up_to_date(self, taskId, dependencies, targets, runOnce):
        """Check if task is up to date.

        @param taskId: (string)
        @param dependencies: (list of string)
        @param runOnce: (bool) task has dependencies but they are not managed
        by doit. they can only be cleared manualy.
        @return: (bool) True if up to date, False needs to re-execute.
        """
        # no dependencies means it is never up to date.
        if (not dependencies) and (not runOnce):
            return False

        # user managed dependency always up-to-date if it exists
        if runOnce:
            if not self._get(taskId,''):
                return False

        # if target file is not there, task is not up to date
        for targ in targets:
            if not os.path.exists(targ):
                return False

        # check for modified dependencies
        for dep in tuple(dependencies):
            if self.modified(taskId,dep):
                return False

        return True
