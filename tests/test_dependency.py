import os

import py.test

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


def pytest_funcarg__depfile(request):
    def create_depfile():
        if os.path.exists(TESTDB): os.remove(TESTDB)
        return Dependency(TESTDB)
    def remove_depfile(depfile):
        if not depfile._closed:
            depfile.close()
        if os.path.exists(TESTDB):
            os.remove(TESTDB)
    return request.cached_setup(
        setup=create_depfile,
        teardown=remove_depfile,
        scope="function")

class TestDependencyDb(object):

    # adding a new value to the DB
    def test_get_set(self, depfile):
        depfile._set("taskId_X","dependency_A","da_md5")
        value = depfile._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    #
    def test_setPersistence(self, depfile):
        # save and close db
        depfile._set("taskId_X","dependency_A","da_md5")
        depfile.close()

        # open it again and check the value
        d2 = Dependency(TESTDB)
        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_corrupted_file(self):
        fd = open(TESTDB, 'w')
        fd.write("""{"x": y}""")
        fd.close()
        py.test.raises(ValueError, Dependency, TESTDB)


    # _get must return None if entry doesnt exist.
    def test_getNonExistent(self, depfile):
        assert depfile._get("taskId_X","dependency_A") == None


    def test_remove(self, depfile):
        depfile._set("taskId_ZZZ","dep_1","12")
        depfile._set("taskId_ZZZ","dep_2","13")
        depfile._set("taskId_YYY","dep_1","14")
        depfile.remove("taskId_ZZZ")
        assert None == depfile._get("taskId_ZZZ","dep_1")
        assert None == depfile._get("taskId_ZZZ","dep_2")
        assert "14" == depfile._get("taskId_YYY","dep_1")


    def test_remove_all(self, depfile):
        depfile._set("taskId_ZZZ","dep_1","12")
        depfile._set("taskId_ZZZ","dep_2","13")
        depfile._set("taskId_YYY","dep_1","14")
        depfile.remove_all()
        assert None == depfile._get("taskId_ZZZ","dep_1")
        assert None == depfile._get("taskId_ZZZ","dep_2")
        assert None == depfile._get("taskId_YYY","dep_1")




class TestSaveSuccess(object):

    def test_save_result(self, depfile):
        t1 = Task('t_name', None)
        t1.result = "result"
        depfile.save_success(t1)
        assert get_md5("result") == depfile._get(t1.name, "result:")

    def test_save_resultNone(self, depfile):
        t1 = Task('t_name', None)
        depfile.save_success(t1)
        assert None is depfile._get(t1.name, "result:")

    def test_save_runonce(self, depfile):
        t1 = Task('t_name', None, [True])
        depfile.save_success(t1)
        assert depfile._get(t1.name, "run-once:")

    def test_save_file_md5(self, depfile):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()

        # save it
        t1 = Task("taskId_X", None, [filePath])
        depfile.save_success(t1)
        expected = "a1bb792202ce163b4f0d17cb264c04e1"
        value = depfile._get("taskId_X",filePath)
        assert expected == value, value

    def test_save_files(self, depfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath2,"w")
        ff.write("part2")
        ff.close()

        assert 0 == len(depfile._db)
        t1 = Task("taskId_X", None, [filePath,filePath2])
        depfile.save_success(t1)
        assert depfile._get("taskId_X",filePath) is not None
        assert depfile._get("taskId_X",filePath2) is not None

    def test_save_result_dep(self, depfile):
        t1 = Task('t1', None)
        t1.result = "result"
        depfile.save_success(t1)
        t2 = Task('t2', None, ['?t1'])
        depfile.save_success(t2)
        assert get_md5(t1.result) == depfile._get("t2", "task:t1")
        t3 = Task('t3', None, [':t1'])
        depfile.save_success(t3)
        assert None is depfile._get("t3", "task:t1")

    def test_save_values(self, depfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        depfile.save_success(t1)
        assert 5 == depfile._get("t1", ":x:")
        assert 10 == depfile._get("t1", ":y:")


class TestGetValue(object):
    def test_ok(self, depfile):
        depfile._set('t1', ':x:', 5)
        assert 5 == depfile.get_value('t1.x')

    def test_invalid_string(self, depfile):
        py.test.raises(Exception, depfile.get_value, 'nono')

    def test_invalid_taskid(self, depfile):
        depfile._set('t1', ':x:', 5)
        py.test.raises(Exception, depfile.get_value, 'nonono.x')

    def test_invalid_arg(self, depfile):
        depfile._set('t1', ':x:', 5)
        py.test.raises(Exception, depfile.get_value, 't1.y')


class TestRemoveSuccess(object):
    def test_save_result(self, depfile):
        t1 = Task('t_name', None)
        t1.result = "result"
        depfile.save_success(t1)
        assert get_md5("result") == depfile._get(t1.name, "result:")
        depfile.remove_success(t1)
        assert None is depfile._get(t1.name, "result:")


class TestIgnore(object):
    def test_save_result(self, depfile):
        t1 = Task('t_name', None)
        depfile.ignore(t1)
        assert '1' == depfile._get(t1.name, "ignore:")


class TestGetStatus(object):

    def test_ignore(self, depfile):
        t1 = Task("t1", None)
        # before ignore
        assert 'run' == depfile.get_status(t1)
        assert [] == t1.dep_changed
        # after ignote
        depfile.ignore(t1)
        assert 'ignore' == depfile.get_status(t1)
        assert [] == t1.dep_changed


    # if there is no dependency the task is always executed
    def test_noDependency(self, depfile):
        t1 = Task("t1", None)
        # first time execute
        assert 'run' == depfile.get_status(t1)
        assert [] == t1.dep_changed
        # second too
        depfile.save_success(t1)
        assert 'run' == depfile.get_status(t1)
        assert [] == t1.dep_changed


    def test_runOnce(self, depfile):
        t1 = Task("t1", None, [True])
        assert 'run' == depfile.get_status(t1)
        assert [] == t1.dep_changed
        depfile.save_success(t1)
        assert 'up-to-date' == depfile.get_status(t1)
        assert [] == t1.dep_changed


    # if target file does not exist, task is outdated.
    def test_targets_notThere(self, depfile):
        dep1 = get_abspath("data/dependency1")
        target = get_abspath("data/target")
        if os.path.exists(target):
            os.remove(target)

        t1 = Task("task x", None, [dep1], [target])
        depfile.save_success(t1)
        assert 'run' == depfile.get_status(t1)
        assert [dep1] == t1.dep_changed


    def test_targets(self, depfile):
        filePath = get_abspath("data/target")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        deps = [get_abspath("data/dependency1")]
        targets = [filePath]
        t1 = Task("task X", None, deps, targets)

        depfile.save_success(t1)
        # up-to-date because target exist
        assert 'up-to-date' == depfile.get_status(t1)
        assert [] == t1.dep_changed


    def test_targetFolder(self, depfile):
        # folder not there. task is not up-to-date
        deps = [get_abspath("data/dependency1")]
        folderPath = get_abspath("data/target-folder")
        if os.path.exists(folderPath):
            os.rmdir(folderPath)
        t1 = Task("task x", None, deps, [folderPath])
        depfile.save_success(t1)

        assert 'run' == depfile.get_status(t1)
        assert deps == t1.dep_changed
        # create folder. task is up-to-date
        os.mkdir(folderPath)
        assert 'up-to-date' == depfile.get_status(t1)
        assert [] == t1.dep_changed


    def test_fileDependencies(self, depfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        dependencies = [filePath]
        t1 = Task("t1", None, dependencies)

        # first time execute
        assert 'run' == depfile.get_status(t1)
        assert dependencies == t1.dep_changed

        # second time no
        depfile.save_success(t1)
        assert 'up-to-date' == depfile.get_status(t1)
        assert [] == t1.dep_changed

        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()

        # execute again
        assert 'run' == depfile.get_status(t1)
        assert dependencies == t1.dep_changed


    def test_resultDependencies(self, depfile):
        # t1 ok, but t2 not saved
        t1 = Task('t1', None)
        t1.result = "result"
        t2 = Task('t2', None, ['?t1'])
        depfile.save_success(t1)
        assert 'run' == depfile.get_status(t2)

        # save t2 - ok
        depfile.save_success(t2)
        assert 'up-to-date' == depfile.get_status(t2)

        # change t1
        t1.result = "another"
        depfile.save_success(t1)
        assert 'run' == depfile.get_status(t2)
