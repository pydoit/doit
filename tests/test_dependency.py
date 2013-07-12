# coding=UTF-8

import os
import time
import six

import pytest

from doit.task import Task
from doit.dependency import get_md5, get_file_md5, check_modified
from doit.dependency import DbmDB, DatabaseException, UptodateCalculator
from doit.dependency import JsonDependency, DbmDependency, SqliteDependency
from .conftest import get_abspath, depfile


def test_unicode_md5():
    data = six.u("我")
    # no exception is raised
    assert get_md5(data)


def test_md5():
    filePath = os.path.join(os.path.dirname(__file__),"sample_md5.txt")
    # result got using command line md5sum
    expected = "45d1503cb985898ab5bd8e58973007dd"
    assert expected == get_file_md5(filePath)


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
# save in db (task - dependency - (timestamp, size, signature))
# taskId_dependency => signature(dependency)
# taskId is md5(CmdTask.task)



# test parametrization, execute tests for all DB backends.
# create a separate fixture to be used only by this module
# because only here it is required to test with all backends
@pytest.fixture
def pdepfile(request):
    return depfile(request)
pytest.fixture(params=[JsonDependency, DbmDependency, SqliteDependency])(pdepfile)

# FIXME there was major refactor breaking classes from dependency,
# unit-tests could be more specific to base classes.

class TestDependencyDb(object):
    # adding a new value to the DB
    def test_get_set(self, pdepfile):
        pdepfile._set("taskId_X","dependency_A","da_md5")
        value = pdepfile._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_get_set_unicode_name(self, pdepfile):
        pdepfile._set(six.u("taskId_我"),"dependency_A","da_md5")
        value = pdepfile._get(six.u("taskId_我"),"dependency_A")
        assert "da_md5" == value, value

    #
    def test_dump(self, pdepfile):
        # save and close db
        pdepfile._set("taskId_X","dependency_A","da_md5")
        pdepfile.close()

        # open it again and check the value
        d2 = pdepfile.__class__(pdepfile.name)

        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_corrupted_file(self, pdepfile):
        if pdepfile.__class__==DbmDependency and pdepfile.whichdb is None: # pragma: no cover
            pytest.skip('dumbdbm too dumb to detect db corruption')

        # create some corrupted files
        for name_ext in pdepfile.name_ext:
            full_name = pdepfile.name + name_ext
            fd = open(full_name, 'w')
            fd.write("""{"x": y}""")
            fd.close()
        pytest.raises(DatabaseException, pdepfile.__class__, pdepfile.name)

    def test_corrupted_file_unrecognized_excep(self, monkeypatch, pdepfile):
        if isinstance(pdepfile, JsonDependency):
            pytest.skip('test doesnt apply to JsonDependency')
        if pdepfile.whichdb is None: # pragma: no cover
            pytest.skip('dumbdbm too dumb to detect db corruption')

        # create some corrupted files
        for name_ext in pdepfile.name_ext:
            full_name = pdepfile.name + name_ext
            fd = open(full_name, 'w')
            fd.write("""{"x": y}""")
            fd.close()
        monkeypatch.setattr(DbmDB, 'DBM_CONTENT_ERROR_MSG', 'xxx')
        pytest.raises(DatabaseException, pdepfile.__class__, pdepfile.name)

    # _get must return None if entry doesnt exist.
    def test_getNonExistent(self, pdepfile):
        assert pdepfile._get("taskId_X","dependency_A") == None


    def test_in(self, pdepfile):
        pdepfile._set("taskId_ZZZ","dep_1","12")
        assert pdepfile._in("taskId_ZZZ")
        assert not pdepfile._in("taskId_hohoho")


    def test_remove(self, pdepfile):
        pdepfile._set("taskId_ZZZ","dep_1","12")
        pdepfile._set("taskId_ZZZ","dep_2","13")
        pdepfile._set("taskId_YYY","dep_1","14")
        pdepfile.remove("taskId_ZZZ")
        assert None == pdepfile._get("taskId_ZZZ","dep_1")
        assert None == pdepfile._get("taskId_ZZZ","dep_2")
        assert "14" == pdepfile._get("taskId_YYY","dep_1")


    # special test for DBM backend and "dirty"/caching mechanism
    def test_remove_from_non_empty_file(self, pdepfile):
        # 1 - put 2 tasks of file
        pdepfile._set("taskId_XXX", "dep_1", "x")
        pdepfile._set("taskId_YYY", "dep_1", "x")
        pdepfile.close()
        # 2 - re-open and remove one task
        reopened = pdepfile.__class__(pdepfile.name)
        reopened.remove("taskId_YYY")
        reopened.close()
        # 3 - re-open again and check task was really removed
        reopened2 = pdepfile.__class__(pdepfile.name)
        assert reopened2._in("taskId_XXX")
        assert not reopened2._in("taskId_YYY")


    def test_remove_all(self, pdepfile):
        pdepfile._set("taskId_ZZZ","dep_1","12")
        pdepfile._set("taskId_ZZZ","dep_2","13")
        pdepfile._set("taskId_YYY","dep_1","14")
        pdepfile.remove_all()
        assert None == pdepfile._get("taskId_ZZZ","dep_1")
        assert None == pdepfile._get("taskId_ZZZ","dep_2")
        assert None == pdepfile._get("taskId_YYY","dep_1")



class TestSaveSuccess(object):

    def test_save_result(self, pdepfile):
        t1 = Task('t_name', None)
        t1.result = "result"
        pdepfile.save_success(t1)
        assert get_md5("result") == pdepfile._get(t1.name, "result:")

    def test_save_resultNone(self, pdepfile):
        t1 = Task('t_name', None)
        pdepfile.save_success(t1)
        assert None is pdepfile._get(t1.name, "result:")

    def test_save_result_dict(self, pdepfile):
        t1 = Task('t_name', None)
        t1.result = {'d': "result"}
        pdepfile.save_success(t1)
        assert {'d': "result"} == pdepfile._get(t1.name, "result:")

    def test_save_file_md5(self, pdepfile):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()

        # save it
        t1 = Task("taskId_X", None, [filePath])
        pdepfile.save_success(t1)
        expected = "a1bb792202ce163b4f0d17cb264c04e1"
        value = pdepfile._get("taskId_X",filePath)
        assert os.path.getmtime(filePath) == value[0] # timestamp
        assert 39 == value[1] # size
        assert expected == value[2] # MD5

    def test_save_skip(self, pdepfile, monkeypatch):
        #self.test_save_file_md5(pdepfile)
        filePath = get_abspath("data/dependency1")
        t1 = Task("taskId_X", None, [filePath])
        pdepfile._set(t1.name, filePath, (345, 0, "fake"))
        monkeypatch.setattr(os.path, 'getmtime', lambda x: 345)
        # save but md5 is not modified
        pdepfile.save_success(t1)
        got = pdepfile._get("taskId_X", filePath)
        assert "fake" == got[2]

    def test_save_files(self, pdepfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath2,"w")
        ff.write("part2")
        ff.close()
        assert pdepfile._get("taskId_X",filePath) is None
        assert pdepfile._get("taskId_X",filePath2) is None

        t1 = Task("taskId_X", None, [filePath,filePath2])
        pdepfile.save_success(t1)
        assert pdepfile._get("taskId_X",filePath) is not None
        assert pdepfile._get("taskId_X",filePath2) is not None

    def test_save_values(self, pdepfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        assert {'x':5, 'y':10} == pdepfile._get("t1", "_values_:")


class TestGetValue(object):
    def test_all_values(self, pdepfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        assert {'x':5, 'y':10} == pdepfile.get_values('t1')

    def test_ok(self, pdepfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        assert 5 == pdepfile.get_value('t1', 'x')

    def test_ok_dot_on_task_name(self, pdepfile):
        t1 = Task('t1:a.ext', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        assert 5 == pdepfile.get_value('t1:a.ext', 'x')

    def test_invalid_taskid(self, pdepfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        pytest.raises(Exception, pdepfile.get_value, 'nonono', 'x')

    def test_invalid_key(self, pdepfile):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdepfile.save_success(t1)
        pytest.raises(Exception, pdepfile.get_value, 't1', 'z')



class TestRemoveSuccess(object):
    def test_save_result(self, pdepfile):
        t1 = Task('t_name', None)
        t1.result = "result"
        pdepfile.save_success(t1)
        assert get_md5("result") == pdepfile._get(t1.name, "result:")
        pdepfile.remove_success(t1)
        assert None is pdepfile._get(t1.name, "result:")


class TestIgnore(object):
    def test_save_result(self, pdepfile):
        t1 = Task('t_name', None)
        pdepfile.ignore(t1)
        assert '1' == pdepfile._get(t1.name, "ignore:")


class TestCheckModified(object):
    def test_None(self, dependency1):
        assert check_modified(dependency1, os.stat(dependency1),  None)

    def test_timestamp(self, dependency1):
        timestamp = os.path.getmtime(dependency1)
        dep_stat = os.stat(dependency1)
        assert not check_modified(dependency1, dep_stat, (timestamp, 0, ''))
        assert check_modified(dependency1, dep_stat, (timestamp+1, 0, ''))

    def test_size_md5(self, dependency1):
        timestamp = os.path.getmtime(dependency1)
        size = os.path.getsize(dependency1)
        md5 = get_file_md5(dependency1)
        dep_stat = os.stat(dependency1)
        # incorrect size dont check md5
        assert check_modified(dependency1, dep_stat, (timestamp+1, size+1, ''))
        # correct size check md5
        assert not check_modified(dependency1, dep_stat, (timestamp+1, size, md5))
        assert check_modified(dependency1, dep_stat, (timestamp+1, size, ''))



class TestGetStatus(object):

    def test_ignore(self, pdepfile):
        t1 = Task("t1", None)
        # before ignore
        assert not pdepfile.status_is_ignore(t1)
        # after ignote
        pdepfile.ignore(t1)
        assert pdepfile.status_is_ignore(t1)


    def test_fileDependencies(self, pdepfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        dependencies = [filePath]
        t1 = Task("t1", None, dependencies)

        # first time execute
        assert 'run' == pdepfile.get_status(t1, {})
        assert dependencies == t1.dep_changed

        # second time no
        pdepfile.save_success(t1)
        assert 'up-to-date' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed

        # FIXME - mock timestamp
        time.sleep(1) # required otherwise timestamp is not modified!
        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()

        # execute again
        assert 'run' == pdepfile.get_status(t1, {})
        assert dependencies == t1.dep_changed


    def test_file_dependency_not_exist(self, pdepfile):
        filePath = get_abspath("data/dependency_not_exist")
        t1 = Task("t1", None, [filePath])
        pytest.raises(Exception, pdepfile.get_status, t1, {})


    # if there is no dependency the task is always executed
    def test_noDependency(self, pdepfile):
        t1 = Task("t1", None)
        # first time execute
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed
        # second too
        pdepfile.save_success(t1)
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed


    def test_UptodateFalse(self, pdepfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = Task("t1", None, file_dep=[filePath], uptodate=[False])

        # first time execute
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed

        # second time execute too
        pdepfile.save_success(t1)
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed

    def test_UptodateTrue(self, pdepfile):
        t1 = Task("t1", None, uptodate=[True])
        pdepfile.save_success(t1)
        assert 'up-to-date' == pdepfile.get_status(t1, {})

    def test_UptodateNone(self, pdepfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = Task("t1", None, file_dep=[filePath], uptodate=[None])

        # first time execute
        assert 'run' == pdepfile.get_status(t1, {})
        assert [filePath] == t1.dep_changed

        # second time execute too
        pdepfile.save_success(t1)
        assert 'up-to-date' == pdepfile.get_status(t1, {})


    def test_UptodateCallable_True(self, pdepfile):
        def check(task, values): return True
        t1 = Task("t1", None, uptodate=[check])
        pdepfile.save_success(t1)
        assert 'up-to-date' == pdepfile.get_status(t1, {})

    def test_UptodateCallable_False(self, pdepfile):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        def check(task, values): return False
        t1 = Task("t1", None, file_dep=[filePath], uptodate=[check])

        # first time execute
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed

        # second time execute too
        pdepfile.save_success(t1)
        assert 'run' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed


    def test_UptodateCallable_added_attributes(self, pdepfile):
        task_dict = "fake dict"
        class My_uptodate(UptodateCalculator):
            def __call__(self, task, values):
                # attributes were added to object before call'ing it
                assert task_dict == self.tasks_dict
                assert None == self.get_val('t1', None)
                return True

        check = My_uptodate()
        t1 = Task("t1", None, uptodate=[check])
        assert 'up-to-date' == pdepfile.get_status(t1, task_dict)


    # if target file does not exist, task is outdated.
    def test_targets_notThere(self, pdepfile, dependency1):
        target = get_abspath("data/target")
        if os.path.exists(target):
            os.remove(target)

        t1 = Task("task x", None, [dependency1], [target])
        pdepfile.save_success(t1)
        assert 'run' == pdepfile.get_status(t1, {})
        assert [dependency1] == t1.dep_changed


    def test_targets(self, pdepfile, dependency1):
        filePath = get_abspath("data/target")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        deps = [dependency1]
        targets = [filePath]
        t1 = Task("task X", None, deps, targets)

        pdepfile.save_success(t1)
        # up-to-date because target exist
        assert 'up-to-date' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed


    def test_targetFolder(self, pdepfile, dependency1):
        # folder not there. task is not up-to-date
        deps = [dependency1]
        folderPath = get_abspath("data/target-folder")
        if os.path.exists(folderPath):
            os.rmdir(folderPath)
        t1 = Task("task x", None, deps, [folderPath])
        pdepfile.save_success(t1)

        assert 'run' == pdepfile.get_status(t1, {})
        assert deps == t1.dep_changed
        # create folder. task is up-to-date
        os.mkdir(folderPath)
        assert 'up-to-date' == pdepfile.get_status(t1, {})
        assert [] == t1.dep_changed
