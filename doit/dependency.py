import anydbm

from doit.util import md5sum

class Dependency(object):
    """ Dependency manager. 
    Each dependency is a saved in dbm. where the key is taskId + dependency (abs file path), and the value is the dependency signature.
    """

    #TODO lazy open DBM.
    def __init__(self, name, clear=False):
        """open/create a DBM
        @param name string filepath of the DBM file
        @param clear boolean always create a new empty database
        """
        self.name = name
        self._closed = False
        if clear:
            self._db = anydbm.open(name,'n')
        else:
            self._db = anydbm.open(name,'c')


    def __del__(self):
        # close db file.
        if not self._closed:
            self._db.close()

    def _set(self, taskId, dependency, value):
        """ store value in the DBM"""
        self._db[taskId+dependency] = value

    def _get(self, taskId, dependency):
        """ @return value stored in the DBM, return None if entry not found"""
        return self._db.get(taskId+dependency,None)

    def save(self, taskId, dependency):
        """ save/update dependency on the DB.
        this method will calculate the value to be stored using md5 and then
        call the _set method.
        """
        self._set(taskId,dependency,md5sum(dependency))

    def modified(self,taskId, dependency):
        """ @return bool if dependency for task was modified or not"""
        return self._get(taskId,dependency) != md5sum(dependency)

    def close(self):
        if not self._closed:
            self._db.close()
            self._closed = True
