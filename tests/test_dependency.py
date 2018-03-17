import os
import time
import sys
import tempfile
import uuid
from sys import executable

import pytest

from doit.task import Task
from doit.dependency import get_md5, get_file_md5
from doit.dependency import DbmDB, JsonDB, SqliteDB, Dependency
from doit.dependency import DatabaseException, UptodateCalculator
from doit.dependency import FileChangedChecker, MD5Checker, TimestampChecker
from doit.dependency import DependencyStatus
from .conftest import get_abspath, dep_manager

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)


def test_unicode_md5():
    data = "我"
    # no exception is raised
    assert get_md5(data)


def test_md5():
    filePath = os.path.join(os.path.dirname(__file__), "sample_md5.txt")
    # result got using command line md5sum, with different line-endings to deal with different GIT
    # configurations:
    expected_lf = "45d1503cb985898ab5bd8e58973007dd"
    expected_crlf = "cf7b48b2fec3b581b135f7c9a1f7ae04"
    assert get_file_md5(filePath) in {expected_lf, expected_crlf}


def test_sqlite_import():
    """
    Checks that SQLite module is not imported until the SQLite class is instantiated
    """
    filename = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))

    assert 'sqlite3' not in sys.modules
    SqliteDB(filename)
    assert 'sqlite3' in sys.modules

    os.remove(filename)

####
# dependencies are files only (not other tasks).
#
# whenever a task has a dependency the runner checks if this dependency
# was modified since last successful run. if not the task is skipped.

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
def pdep_manager(request):
    return dep_manager(request)
pytest.fixture(params=[JsonDB, DbmDB, SqliteDB])(pdep_manager)

# FIXME there was major refactor breaking classes from dependency,
# unit-tests could be more specific to base classes.

class TestDependencyDb(object):
    # adding a new value to the DB
    def test_get_set(self, pdep_manager):
        pdep_manager._set("taskId_X","dependency_A","da_md5")
        value = pdep_manager._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_get_set_unicode_name(self, pdep_manager):
        pdep_manager._set("taskId_我", "dependency_A", "da_md5")
        value = pdep_manager._get("taskId_我", "dependency_A")
        assert "da_md5" == value, value

    #
    def test_dump(self, pdep_manager):
        # save and close db
        pdep_manager._set("taskId_X","dependency_A","da_md5")
        pdep_manager.close()

        # open it again and check the value
        d2 = Dependency(pdep_manager.db_class, pdep_manager.name)

        value = d2._get("taskId_X","dependency_A")
        assert "da_md5" == value, value

    def test_corrupted_file(self, pdep_manager):
        if pdep_manager.whichdb is None: # pragma: no cover
            pytest.skip('dumbdbm too dumb to detect db corruption')

        # create some corrupted files
        for name_ext in pdep_manager.name_ext:
            full_name = pdep_manager.name + name_ext
            fd = open(full_name, 'w')
            fd.write("""{"x": y}""")
            fd.close()
        pytest.raises(DatabaseException, Dependency,
                      pdep_manager.db_class, pdep_manager.name)

    def test_corrupted_file_unrecognized_excep(self, monkeypatch, pdep_manager):
        if pdep_manager.db_class is not DbmDB:
            pytest.skip('test doesnt apply to non DBM DB')
        if pdep_manager.whichdb is None: # pragma: no cover
            pytest.skip('dumbdbm too dumb to detect db corruption')

        # create some corrupted files
        for name_ext in pdep_manager.name_ext:
            full_name = pdep_manager.name + name_ext
            fd = open(full_name, 'w')
            fd.write("""{"x": y}""")
            fd.close()
        monkeypatch.setattr(DbmDB, 'DBM_CONTENT_ERROR_MSG', 'xxx')
        pytest.raises(DatabaseException, Dependency,
                      pdep_manager.db_class, pdep_manager.name)

    # _get must return None if entry doesnt exist.
    def test_getNonExistent(self, pdep_manager):
        assert pdep_manager._get("taskId_X","dependency_A") == None


    def test_in(self, pdep_manager):
        pdep_manager._set("taskId_ZZZ","dep_1","12")
        assert pdep_manager._in("taskId_ZZZ")
        assert not pdep_manager._in("taskId_hohoho")


    def test_remove(self, pdep_manager):
        pdep_manager._set("taskId_ZZZ","dep_1","12")
        pdep_manager._set("taskId_ZZZ","dep_2","13")
        pdep_manager._set("taskId_YYY","dep_1","14")
        pdep_manager.remove("taskId_ZZZ")
        assert None == pdep_manager._get("taskId_ZZZ","dep_1")
        assert None == pdep_manager._get("taskId_ZZZ","dep_2")
        assert "14" == pdep_manager._get("taskId_YYY","dep_1")


    # special test for DBM backend and "dirty"/caching mechanism
    def test_remove_from_non_empty_file(self, pdep_manager):
        # 1 - put 2 tasks of file
        pdep_manager._set("taskId_XXX", "dep_1", "x")
        pdep_manager._set("taskId_YYY", "dep_1", "x")
        pdep_manager.close()
        # 2 - re-open and remove one task
        reopened = Dependency(pdep_manager.db_class, pdep_manager.name)
        reopened.remove("taskId_YYY")
        reopened.close()
        # 3 - re-open again and check task was really removed
        reopened2 = Dependency(pdep_manager.db_class, pdep_manager.name)
        assert reopened2._in("taskId_XXX")
        assert not reopened2._in("taskId_YYY")


    def test_remove_all(self, pdep_manager):
        pdep_manager._set("taskId_ZZZ","dep_1","12")
        pdep_manager._set("taskId_ZZZ","dep_2","13")
        pdep_manager._set("taskId_YYY","dep_1","14")
        pdep_manager.remove_all()
        assert None == pdep_manager._get("taskId_ZZZ","dep_1")
        assert None == pdep_manager._get("taskId_ZZZ","dep_2")
        assert None == pdep_manager._get("taskId_YYY","dep_1")


class TestSaveSuccess(object):

    def test_save_result(self, pdep_manager):
        t1 = Task('t_name', None)
        t1.result = "result"
        pdep_manager.save_success(t1)
        assert get_md5("result") == pdep_manager._get(t1.name, "result:")
        assert get_md5("result") == pdep_manager.get_result(t1.name)

    def test_save_result_hash(self, pdep_manager):
        t1 = Task('t_name', None)
        t1.result = "result"
        pdep_manager.save_success(t1, result_hash='abc')
        assert 'abc' == pdep_manager._get(t1.name, "result:")

    def test_save_resultNone(self, pdep_manager):
        t1 = Task('t_name', None)
        pdep_manager.save_success(t1)
        assert None is pdep_manager._get(t1.name, "result:")

    def test_save_result_dict(self, pdep_manager):
        t1 = Task('t_name', None)
        t1.result = {'d': "result"}
        pdep_manager.save_success(t1)
        assert {'d': "result"} == pdep_manager._get(t1.name, "result:")

    def test_save_file_md5(self, pdep_manager):
        # create a test dependency file
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("i am the first dependency ever for doit")
        ff.close()

        # save it
        t1 = Task("taskId_X", None, [filePath])
        pdep_manager.save_success(t1)
        expected = "a1bb792202ce163b4f0d17cb264c04e1"
        value = pdep_manager._get("taskId_X",filePath)
        assert os.path.getmtime(filePath) == value[0] # timestamp
        assert 39 == value[1] # size
        assert expected == value[2] # MD5

    def test_save_skip(self, pdep_manager, monkeypatch):
        #self.test_save_file_md5(pdep_manager)
        filePath = get_abspath("data/dependency1")
        t1 = Task("taskId_X", None, [filePath])
        pdep_manager._set(t1.name, filePath, (345, 0, "fake"))
        monkeypatch.setattr(os.path, 'getmtime', lambda x: 345)
        # save but md5 is not modified
        pdep_manager.save_success(t1)
        got = pdep_manager._get("taskId_X", filePath)
        assert "fake" == got[2]

    def test_save_files(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath2,"w")
        ff.write("part2")
        ff.close()
        assert pdep_manager._get("taskId_X",filePath) is None
        assert pdep_manager._get("taskId_X",filePath2) is None

        t1 = Task("taskId_X", None, [filePath,filePath2])
        pdep_manager.save_success(t1)
        assert pdep_manager._get("taskId_X",filePath) is not None
        assert pdep_manager._get("taskId_X",filePath2) is not None
        assert set(pdep_manager._get("taskId_X", 'deps:')) == t1.file_dep

    def test_save_values(self, pdep_manager):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        assert {'x':5, 'y':10} == pdep_manager._get("t1", "_values_:")


class TestGetValue(object):
    def test_all_values(self, pdep_manager):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        assert {'x':5, 'y':10} == pdep_manager.get_values('t1')

    def test_ok(self, pdep_manager):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        assert 5 == pdep_manager.get_value('t1', 'x')

    def test_ok_dot_on_task_name(self, pdep_manager):
        t1 = Task('t1:a.ext', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        assert 5 == pdep_manager.get_value('t1:a.ext', 'x')

    def test_invalid_taskid(self, pdep_manager):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        pytest.raises(Exception, pdep_manager.get_value, 'nonono', 'x')

    def test_invalid_key(self, pdep_manager):
        t1 = Task('t1', None)
        t1.values = {'x':5, 'y':10}
        pdep_manager.save_success(t1)
        pytest.raises(Exception, pdep_manager.get_value, 't1', 'z')


class TestRemoveSuccess(object):
    def test_save_result(self, pdep_manager):
        t1 = Task('t_name', None)
        t1.result = "result"
        pdep_manager.save_success(t1)
        assert get_md5("result") == pdep_manager._get(t1.name, "result:")
        pdep_manager.remove_success(t1)
        assert None is pdep_manager._get(t1.name, "result:")


class TestIgnore(object):
    def test_save_result(self, pdep_manager):
        t1 = Task('t_name', None)
        pdep_manager.ignore(t1)
        assert '1' == pdep_manager._get(t1.name, "ignore:")


class TestMD5Checker(object):
    def test_timestamp(self, dependency1):
        checker = MD5Checker()
        state = checker.get_state(dependency1, None)
        state2 = (state[0], state[1]+1, '')
        file_stat = os.stat(dependency1)
        # dep considered the same as long as timestamp is unchanged
        assert not checker.check_modified(dependency1, file_stat, state2)

    def test_size(self, dependency1):
        checker = MD5Checker()
        state = checker.get_state(dependency1, None)
        state2 = (state[0]+1, state[1]+1, state[2])
        file_stat = os.stat(dependency1)
        # if size changed for sure modified (md5 is not checked)
        assert checker.check_modified(dependency1, file_stat, state2)

    def test_md5(self, dependency1):
        checker = MD5Checker()
        state = checker.get_state(dependency1, None)
        file_stat = os.stat(dependency1)
        # same size and md5
        state2 = (state[0]+1, state[1], state[2])
        assert not checker.check_modified(dependency1, file_stat, state2)
        # same size, different md5
        state3 = (state[0]+1, state[1], 'not me')
        assert checker.check_modified(dependency1, file_stat, state3)


class TestCustomChecker(object):

    def test_not_implemented(self, dependency1):
        class MyChecker(FileChangedChecker):
            pass

        checker = MyChecker()
        pytest.raises(NotImplementedError, checker.get_state, None, None)
        pytest.raises(NotImplementedError, checker.check_modified,
                      None, None, None)


class TestTimestampChecker(object):
    def test_timestamp(self, dependency1):
        checker = TimestampChecker()
        state = checker.get_state(dependency1, None)
        file_stat = os.stat(dependency1)
        assert not checker.check_modified(dependency1, file_stat, state)
        assert checker.check_modified(dependency1, file_stat, state+1)


class TestDependencyStatus(object):
    def test_add_reason(self):
        result = DependencyStatus(True)
        assert 'up-to-date' == result.status
        assert not result.add_reason('changed_file_dep', 'f1')
        assert 'run' == result.status
        assert not result.add_reason('changed_file_dep', 'f2')
        assert ['f1', 'f2'] == result.reasons['changed_file_dep']

    def test_add_reason_error(self):
        result = DependencyStatus(True)
        assert 'up-to-date' == result.status
        assert not result.add_reason('missing_file_dep', 'f1', 'error')
        assert 'error' == result.status
        assert ['f1'] == result.reasons['missing_file_dep']

    def test_set_reason(self):
        result = DependencyStatus(True)
        assert 'up-to-date' == result.status
        assert not result.set_reason('has_no_dependencies', True)
        assert 'run' == result.status
        assert True == result.reasons['has_no_dependencies']

    def test_no_log(self):
        result = DependencyStatus(False)
        assert 'up-to-date' == result.status
        assert result.set_reason('has_no_dependencies', True)
        assert 'run' == result.status

    def test_get_error_message(self):
        result = DependencyStatus(False)
        assert None == result.get_error_message()
        result.error_reason = 'foo xxx'
        assert 'foo xxx' == result.get_error_message()



class TestGetStatus(object):

    def test_ignore(self, pdep_manager):
        t1 = Task("t1", None)
        # before ignore
        assert not pdep_manager.status_is_ignore(t1)
        # after ignote
        pdep_manager.ignore(t1)
        assert pdep_manager.status_is_ignore(t1)


    def test_fileDependencies(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        dependencies = [filePath]
        t1 = Task("t1", None, dependencies)

        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert dependencies == t1.dep_changed

        # second time no
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

        # FIXME - mock timestamp
        time.sleep(1) # required otherwise timestamp is not modified!
        # a small change on the file
        ff = open(filePath,"a")
        ff.write(" part2")
        ff.close()

        # execute again
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert dependencies == t1.dep_changed

    def test_fileDependencies_changed(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        dependencies = [filePath, filePath2]
        t1 = Task("t1", None, dependencies)

        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert sorted(dependencies) == sorted(t1.dep_changed)

        # second time no
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

        # remove dependency filePath2
        t1 = Task("t1", None, [filePath])
        # execute again
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed


    def test_fileDependencies_changed_get_log(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        filePath2 = get_abspath("data/dependency2")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = Task("t1", None, [filePath])

        # first time execute
        result = pdep_manager.get_status(t1, {}, get_log=True)
        assert 'run' == result.status
        assert [filePath] == t1.dep_changed
        pdep_manager.save_success(t1)

        # second time
        t1b = Task("t1", None, [filePath2])
        result = pdep_manager.get_status(t1b, {}, get_log=True)
        assert 'run' == result.status
        assert [filePath2] == t1b.dep_changed
        assert [filePath] == result.reasons['removed_file_dep']
        assert [filePath2] == result.reasons['added_file_dep']


    def test_file_dependency_not_exist(self, pdep_manager):
        filePath = get_abspath("data/dependency_not_exist")
        t1 = Task("t1", None, [filePath])
        assert 'error' == pdep_manager.get_status(t1, {}).status


    def test_change_checker(self, pdep_manager, dependency1):
        t1 = Task("taskId_X", None, [dependency1])
        pdep_manager.checker = TimestampChecker()
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status
        # change of checker force `run` again
        pdep_manager.checker = MD5Checker()
        assert 'run' == pdep_manager.get_status(t1, {}).status
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status


    # if there is no dependency the task is always executed
    def test_noDependency(self, pdep_manager):
        t1 = Task("t1", None)
        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed
        # second too
        pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed


    def test_UptodateFalse(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = Task("t1", None, file_dep=[filePath], uptodate=[False])

        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

        # second time execute too
        pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

    def test_UptodateTrue(self, pdep_manager):
        t1 = Task("t1", None, uptodate=[True])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateNone(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        t1 = Task("t1", None, file_dep=[filePath], uptodate=[None])

        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [filePath] == t1.dep_changed

        # second time execute too
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status


    def test_UptodateFunction_True(self, pdep_manager):
        def check(task, values):
            assert task.name == 't1'
            return True
        t1 = Task("t1", None, uptodate=[check])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateFunction_False(self, pdep_manager):
        filePath = get_abspath("data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        def check(task, values): return False
        t1 = Task("t1", None, file_dep=[filePath], uptodate=[check])

        # first time execute
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

        # second time execute too
        pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed

    def test_UptodateFunction_without_args_True(self, pdep_manager):
        def check(): return True
        t1 = Task("t1", None, uptodate=[check])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_uptodate_call_all_even_if_some_False(self, pdep_manager):
        checks = []
        def check():
            checks.append(1)
            return False
        t1 = Task("t1", None, uptodate=[check, check])
        #pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert 2 == len(checks)


    def test_UptodateFunction_extra_args_True(self, pdep_manager):
        def check(task, values, control):
            assert task.name == 't1'
            return control>30
        t1 = Task("t1", None, uptodate=[ (check, [34]) ])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateCallable_True(self, pdep_manager):
        class MyChecker(object):
            def __call__(self, task, values):
                assert task.name == 't1'
                return True
        t1 = Task("t1", None, uptodate=[ MyChecker() ])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateMethod_True(self, pdep_manager):
        class MyChecker(object):
            def check(self, task, values):
                assert task.name == 't1'
                return True
        t1 = Task("t1", None, uptodate=[ MyChecker().check ])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateCallable_added_attributes(self, pdep_manager):
        task_dict = "fake dict"
        class My_uptodate(UptodateCalculator):
            def __call__(self, task, values):
                # attributes were added to object before call'ing it
                assert task_dict == self.tasks_dict
                assert None == self.get_val('t1', None)
                return True

        check = My_uptodate()
        t1 = Task("t1", None, uptodate=[check])
        assert 'up-to-date' == pdep_manager.get_status(t1, task_dict).status

    def test_UptodateCommand_True(self, pdep_manager):
        t1 = Task("t1", None, uptodate=[PROGRAM])
        pdep_manager.save_success(t1)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status

    def test_UptodateCommand_False(self, pdep_manager):
        t1 = Task("t1", None, uptodate=[PROGRAM + ' please fail'])
        pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status


    # if target file does not exist, task is outdated.
    def test_targets_notThere(self, pdep_manager, dependency1):
        target = get_abspath("data/target")
        if os.path.exists(target):
            os.remove(target)

        t1 = Task("task x", None, [dependency1], [target])
        pdep_manager.save_success(t1)
        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert [dependency1] == t1.dep_changed


    def test_targets(self, pdep_manager, dependency1):
        filePath = get_abspath("data/target")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        deps = [dependency1]
        targets = [filePath]
        t1 = Task("task X", None, deps, targets)

        pdep_manager.save_success(t1)
        # up-to-date because target exist
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed


    def test_targetFolder(self, pdep_manager, dependency1):
        # folder not there. task is not up-to-date
        deps = [dependency1]
        folderPath = get_abspath("data/target-folder")
        if os.path.exists(folderPath):
            os.rmdir(folderPath)
        t1 = Task("task x", None, deps, [folderPath])
        pdep_manager.save_success(t1)

        assert 'run' == pdep_manager.get_status(t1, {}).status
        assert deps == t1.dep_changed
        # create folder. task is up-to-date
        os.mkdir(folderPath)
        assert 'up-to-date' == pdep_manager.get_status(t1, {}).status
        assert [] == t1.dep_changed
