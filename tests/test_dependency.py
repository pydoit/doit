import os

from doit.dependency import md5sum, Dependency


def get_abspath(relativePath):
    """ return abs file path relative to this file"""
    return os.path.join(os.path.dirname(__file__), relativePath)



def test_md5():
    filePath = os.path.join(os.path.dirname(__file__),"sample_md5.txt")
    # result got using command line md5sum
    expected = "45d1503cb985898ab5bd8e58973007dd"
    assert expected == md5sum(filePath)


####
# dependencies are files only (not other tasks), or bool.
#
# whenever a task has a dependency the runner checks if this dependency
# was modified since last successful run. if not the task is skipped.
# if depedency is a bool. it is always up-to-date if present.

# since more than one task might have the same dependency, and the tasks
# might have different results (success/failure). the signature is associated
# not only with the file, but also with the task.
#
# save in db (task - dependency - signature)
# taskId_dependency => signature(dependency)
# taskId is md5(CmdTask.task)

TESTDB = "testdb"

class DependencyTestBase(object):
    def setUp(self):
        if os.path.exists(TESTDB): os.remove(TESTDB)
        self.d = Dependency(TESTDB)

    def tearDown(self):
        if not self.d._closed:
            self.d.close()
        if os.path.exists(TESTDB):
            os.remove(TESTDB)

class TestDependencyDb(DependencyTestBase):

    # adding a new value to the DB
    def test_getSet(self):
        self.d._set("taskId_X","dependency_A","da_md5")
        value = self.d._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    #
    def test_setPersistence(self):
        # save and close db
        self.d._set("taskId_X","dependency_A","da_md5")
        self.d.close()

        # open it again and check the value
        d2 = Dependency(TESTDB)
        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_new(self):
        # save and close db
        self.d._set("taskId_X","dependency_A","da_md5")
        self.d.close()

        # open same file but with new parameter
        d2 = Dependency(TESTDB, new=True)
        assert 0 == len(d2._db)


    # _get must return None if entry doesnt exist.
    def test_getNonExistent(self):
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

    def test_remove(self):
        self.d._set("taskId_ZZZ","dep_1","12")
        self.d._set("taskId_ZZZ","dep_2","13")
        self.d._set("taskId_YYY","dep_1","14")
        self.d.remove("taskId_ZZZ")
        assert None == self.d._get("taskId_ZZZ","dep_1")
        assert None == self.d._get("taskId_ZZZ","dep_2")
        assert "14" == self.d._get("taskId_YYY","dep_1")

    def test_remove_all(self):
        self.d._set("taskId_ZZZ","dep_1","12")
        self.d._set("taskId_ZZZ","dep_2","13")
        self.d._set("taskId_YYY","dep_1","14")
        self.d.remove_all()
        assert None == self.d._get("taskId_ZZZ","dep_1")
        assert None == self.d._get("taskId_ZZZ","dep_2")
        assert None == self.d._get("taskId_YYY","dep_1")


    def test_notModified(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()
        # save it
        self.d.save("taskId_X",filePath)

        assert not self.d.modified("taskId_X",filePath)

    def test_yesModified(self):
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
    def test_notThereModified(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency_notthere")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()
        assert self.d.modified("taskId_X",filePath)



class TestTaskDependency(DependencyTestBase):

    # whenever a task has a dependency the runner checks if this dependency
    # was modified since last successful run. if not the task is skipped.

    def test_saveDependencies(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath2,"w")
        ff.write("part2")
        ff.close()

        assert 0 == len(self.d._db)
        self.d.save_dependencies("taskId_X",[filePath,filePath2])
        assert self.d._get("taskId_X",filePath) is not None
        assert self.d._get("taskId_X",filePath2) is not None


    # if there is no dependency the task is always executed
    def test_upToDate_noDependency(self):
        taskId = "task A"
        # first time execute
        assert self.d.up_to_date(taskId,[],[],False,[]) == (False, [])
        # second too
        assert self.d.up_to_date(taskId,[],[],False,[]) == (False, [])


    # if there is a dependency the task is executed only if one of
    # the dependencies were modified
    def test_upToDate_dependencies(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        taskId = "task X";
        dependencies = [filePath]
        # first time execute
        up_to_date, changed = self.d.up_to_date(taskId,dependencies,[],False,[])
        assert  (up_to_date, changed)== (False, dependencies)

        self.d.save_dependencies(taskId,dependencies)
        # second time no
        assert self.d.up_to_date(taskId,dependencies,[],False,[]) == (True, [])

        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()

        # execute again
        up_to_date3, changed3 = self.d.up_to_date(taskId,dependencies,[],False,[])
        assert  (up_to_date3, changed3) == (False, dependencies)


    # if target file does not exist, task is outdated.
    def test_upToDate_targets_notThere(self):
        deps = [get_abspath("data/dependency1")]
        taskId = "task x"
        self.d.save_dependencies(taskId,deps)

        filePath = get_abspath("data/target")
        if os.path.exists(filePath):
            os.remove(filePath)

        uptodate,changed = self.d.up_to_date(taskId,deps,[filePath],False,[])
        assert (uptodate, changed) == (False, deps)

    def test_upToDate_targets(self):
        filePath = get_abspath("data/target")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        taskId = "task X";
        deps = [get_abspath("data/dependency1")]
        targets = [filePath]
        self.d.save_dependencies(taskId,deps)

        # up-to-date because target exist
        uptodate, changed = self.d.up_to_date(taskId,deps,targets,False,[])
        assert (uptodate, changed) == (True, [])

    def test_upToDate_targetFolder(self):
        # folder not there. task is not up-to-date
        deps = [get_abspath("data/dependency1")]
        taskId = "task x"
        self.d.save_dependencies(taskId,deps)
        folderPath = get_abspath("data/target-folder")
        if os.path.exists(folderPath):
            os.rmdir(folderPath)
        uptodate, changed = self.d.up_to_date(taskId,deps,[folderPath],False,[])
        assert (uptodate, changed) == (False, deps)
        # create folder. task is up-to-date
        os.mkdir(folderPath)
        uptodate2, changed2 = self.d.up_to_date(taskId,deps,[folderPath],False,[])
        assert (uptodate2, changed2) == (True, [])

class TestRunOnceDependency(DependencyTestBase):

    def test_upToDate_BoolDependency(self):
        taskId = "task X"
        assert self.d.up_to_date(taskId,[],[],True,[]) == (False, [])
        self.d.save_run_once(taskId)
        assert self.d.up_to_date(taskId,[],[],True,[]) == (True, [])
