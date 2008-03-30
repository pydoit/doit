"""Manage (save/check) task dependency-on-files data."""

import os
import anydbm

from doit.util import md5sum

class Dependency(object):
    """Manage dependency on files.

    Each dependency is a saved in dbm. where the key is taskId + dependency 
    (abs file path), and the value is the dependency signature.
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

    def save_dependencies(self,taskId, dependencies):
        """Save dependencies value.

        @param taskId: (string)
        @param dependencies: (list of string)
        """
        for dep in dependencies:
            self.save(taskId,dep)

    def up_to_date(self, taskId, dependencies, targets):
        """Check if task is up to date.

        @param taskId: (string)
        @param dependencies: (list of string)
        @return: (bool) True if up to date, False needs to re-execute.
        """
        # no dependencies means it is never up to date.
        if not dependencies:
            return False

        # if target file is not there, task is not up to date
        for targ in targets:
            if not os.path.exists(targ):
                return False

        # check for dependencies 
        for dep in tuple(dependencies) + tuple(targets):
            if self.modified(taskId,dep):
                return False
                
        return True
