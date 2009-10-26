import os

from doit.task import Task
from doit.dependency import get_md5, md5sum, Dependency


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
    def test_get_set(self):
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




class TestSaveSuccess(DependencyTestBase):

    def test_save_result(self):
        t1 = Task('t_name', None)
        t1.value = "result"
        self.d.save_success(t1)
        assert get_md5("result") == self.d._get(t1.name, "result:")

    def test_save_resultNone(self):
        t1 = Task('t_name', None)
        self.d.save_success(t1)
        assert None is self.d._get(t1.name, "result:")

    def test_save_runonce(self):
        t1 = Task('t_name', None, [True])
        self.d.save_success(t1)
        assert self.d._get(t1.name, "run-once:")

    def test_save_file_md5(self):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()

        # save it
        t1 = Task("taskId_X", None, [filePath])
        self.d.save_success(t1)
        expected = "a1bb792202ce163b4f0d17cb264c04e1"
        value = self.d._get("taskId_X",filePath)
        assert expected == value, value

    def test_save_files(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath2,"w")
        ff.write("part2")
        ff.close()

        assert 0 == len(self.d._db)
        t1 = Task("taskId_X", None, [filePath,filePath2])
        self.d.save_success(t1)
        assert self.d._get("taskId_X",filePath) is not None
        assert self.d._get("taskId_X",filePath2) is not None

    def test_save_result_dep(self):
        t1 = Task('t1', None)
        t1.value = "result"
        self.d.save_success(t1)
        t2 = Task('t2', None, ['?t1'])
        self.d.save_success(t2)
        assert get_md5(t1.value) == self.d._get("t2", "task:t1")
        t3 = Task('t3', None, [':t1'])
        self.d.save_success(t3)
        assert None is self.d._get("t3", "task:t1")


class TestRemoveSuccess(DependencyTestBase):
    def test_save_result(self):
        t1 = Task('t_name', None)
        t1.value = "result"
        self.d.save_success(t1)
        assert get_md5("result") == self.d._get(t1.name, "result:")
        self.d.remove_success(t1)
        assert None is self.d._get(t1.name, "result:")


class TestUpToDate(DependencyTestBase):

    # if there is no dependency the task is always executed
    def test_noDependency(self):
        t1 = Task("t1", None)
        # first time execute
        assert False == self.d.up_to_date(t1)
        assert [] == t1.dep_changed
        # second too
        self.d.save_success(t1)
        assert False == self.d.up_to_date(t1)
        assert [] == t1.dep_changed


    def test_runOnce(self):
        t1 = Task("t1", None, [True])
        assert False == self.d.up_to_date(t1)
        assert [] == t1.dep_changed
        self.d.save_success(t1)
        assert True == self.d.up_to_date(t1)
        assert [] == t1.dep_changed


    # if target file does not exist, task is outdated.
    def test_targets_notThere(self):
        dep1 = get_abspath("data/dependency1")
        target = get_abspath("data/target")
        if os.path.exists(target):
            os.remove(target)

        t1 = Task("task x", None, [dep1], [target])
        self.d.save_success(t1)
        assert False == self.d.up_to_date(t1)
        assert [dep1] == t1.dep_changed


    def test_targets(self):
        filePath = get_abspath("data/target")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        deps = [get_abspath("data/dependency1")]
        targets = [filePath]
        t1 = Task("task X", None, deps, targets)

        self.d.save_success(t1)
        # up-to-date because target exist
        assert True == self.d.up_to_date(t1)
        assert [] == t1.dep_changed


    def test_targetFolder(self):
        # folder not there. task is not up-to-date
        deps = [get_abspath("data/dependency1")]
        folderPath = get_abspath("data/target-folder")
        if os.path.exists(folderPath):
            os.rmdir(folderPath)
        t1 = Task("task x", None, deps, [folderPath])
        self.d.save_success(t1)

        assert False == self.d.up_to_date(t1)
        assert deps == t1.dep_changed
        # create folder. task is up-to-date
        os.mkdir(folderPath)
        assert True == self.d.up_to_date(t1)
        assert [] == t1.dep_changed


    def test_fileDependencies(self):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        dependencies = [filePath]
        t1 = Task("t1", None, dependencies)

        # first time execute
        assert False == self.d.up_to_date(t1)
        assert dependencies == t1.dep_changed

        # second time no
        self.d.save_success(t1)
        assert True == self.d.up_to_date(t1)
        assert [] == t1.dep_changed

        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()

        # execute again
        assert False == self.d.up_to_date(t1)
        assert dependencies == t1.dep_changed


    def test_resultDependencies(self):
        # t1 ok, but t2 not saved
        t1 = Task('t1', None)
        t1.value = "result"
        t2 = Task('t2', None, ['?t1'])
        self.d.save_success(t1)
        assert False == self.d.up_to_date(t2)

        # save t2 - ok
        self.d.save_success(t2)
        assert True == self.d.up_to_date(t2)

        # change t1
        t1.value = "another"
        self.d.save_success(t1)
        assert False == self.d.up_to_date(t2)
