import os 

from doit.core import BaseTask
from doit.dependency import Dependency

####
# dependencies are files only (not other tasks).
#
# whenever a task has a dependency the runner checks if this dependency
# was modified since last successful run. if not the task is skipped.

# if the task is executed and successful the dependency timestamp is updated.


# Python callable
#  
#           md5(PythonTask.task.__module__ + ..__class__ + ..__name__ +
#                 ..__hash__)

# att\callable     func           class    method
# __module__       ok             ok       ok
# __name__         ok             ok       ok
# __class__        function       no       instancemethod
# __hash__         runtime        no       runtime
# type
# runtime parameters ...

# use shelve

#3 retrieve from DB
#4 compare 1
#5 compare all

# 
def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.abspath(__file__+"/../"+relativePath)


class TestTaskSignature(object):

    # if the task is different the signature must be different. (
    def testSinatureDiffers(self):
        t1 = BaseTask(['ls','-1'])
        t2 = BaseTask(['ls','-2'])
        assert t1.signature() != t2.signature()

    # 2 different instances with the same content has the same signature
    def testSinatureEqual(self):
        t1 = BaseTask(['ls','-1'])
        t2 = BaseTask(['ls','-1'])
        assert t1.signature() == t2.signature()


#TODO task signature for PythonTask(s)



# since more than one task might have the same dependency, and the tasks
# might have different results (success/failure). the timestamp be associated
# not only with the file, but also with the task.
#
# save in db (task - dependency - signature)
# taskId_dependency => signature(dependency)
# taskId is md5(CmdTask.task)

class TestDependencyDb(object):

    def setUp(self):
        self.d = Dependency("testdbm", clear=True)

    # adding a new value to the DB
    def test_set(self):
        self.d._set("taskId_X","dependency_A","da_md5")
        value = self.d._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    # 
    def test_set_persistence(self):
        # save and close db
        self.d._set("taskId_X","dependency_A","da_md5")
        del self.d

        # open it again and check the value
        d2 = Dependency("testdbm")
        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value
        

    # _get must return None if entry doesnt exist.
    def test_get_nonexistent(self):
        assert self.d._get("taskId_X","dependency_A") == None


    def test_save(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()

        # save it
        self.d.save("taskId_X",filePath)
        expected = "a1bb792202ce163b4f0d17cb264c04e1"
        value = self.d._get("taskId_X",filePath)
        assert expected == value, value
        
    def test_not_modified(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()      
        # save it
        self.d.save("taskId_X",filePath)
        
        assert not self.d.modified("taskId_X",filePath)
        
    def test_yes_modified(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()
        # save it
        self.d.save("taskId_X",filePath)
        # modifiy
        ff = open(filePath,"a")
        ff.write(" - with the first modification!")
        ff.close()
        
        assert self.d.modified("taskId_X",filePath)

    # if there is no entry for dependency. it is like modified.
    def test_notthere_modified(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency_notthere")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()
        assert self.d.modified("taskId_X",filePath)

class TestTaskExecution(object):

    # whenever a task has a dependency the runner checks if this dependency
    # was modified since last successful run. if not the task is skipped.    

    # if there is no dependency the task is always executed
    def test_no_dependency(self):
        t1 = BaseTask("task A")
        # first time execute
        assert t1.check_execute()        
        # second too
        assert t1.check_execute()


    # if there is a dependency the task is executed only if one of
    # the dependencies were modified
    def test_dependency(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = BaseTask("task A",dependencies=[filePath])
        # first time execute
        assert t1.check_execute()        
        # second time no
        assert not t1.check_execute()

        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()
        
        # execute again
        assert t1.check_execute()        

