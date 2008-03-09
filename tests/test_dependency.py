import os 

from doit.dependency import Dependency


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.abspath(__file__+"/../"+relativePath)


####
# dependencies are files only (not other tasks).
#
# whenever a task has a dependency the runner checks if this dependency
# was modified since last successful run. if not the task is skipped.


# since more than one task might have the same dependency, and the tasks
# might have different results (success/failure). the signature is associated
# not only with the file, but also with the task.
#
# save in db (task - dependency - signature)
# taskId_dependency => signature(dependency)
# taskId is md5(CmdTask.task)

TESTDBM = "testdbm"
class DependencyTestBase(object):
    def setUp(self):
        self.d = Dependency(TESTDBM)

    def tearDown(self):
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

class TestDependencyDb(DependencyTestBase):

    # adding a new value to the DB
    def test_set(self):
        self.d._set("taskId_X","dependency_A","da_md5")
        value = self.d._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    # 
    def test_setPersistence(self):
        # save and close db
        self.d._set("taskId_X","dependency_A","da_md5")
        del self.d

        # open it again and check the value
        d2 = Dependency(TESTDBM)
        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value
        
    def test_new(self):
        # save and close db
        self.d._set("taskId_X","dependency_A","da_md5")
        del self.d

        # open same file but with new parameter
        d2 = Dependency(TESTDBM, new=True)
        assert 0 == len(d2._db)
        

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



class TestTaskExecution(DependencyTestBase):
        
    # whenever a task has a dependency the runner checks if this dependency
    # was modified since last successful run. if not the task is skipped.    

    # if there is no dependency the task is always executed
    def test_no_dependency(self):
        taskId = "task A"
        # first time execute
        assert not self.d.up_to_date(taskId,[])        
        # second too
        assert not self.d.up_to_date(taskId,[])


    # if there is a dependency the task is executed only if one of
    # the dependencies were modified
    def test_dependency(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        taskId = "task X";
        dependencies = [filePath]
        # first time execute
        assert not self.d.up_to_date(taskId,dependencies)
        self.d.save_dependencies(taskId,dependencies)
        # second time no
        assert self.d.up_to_date(taskId,dependencies)

        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()
        
        # execute again
        assert not self.d.up_to_date(taskId,dependencies)

