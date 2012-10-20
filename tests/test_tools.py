# coding=UTF-8

import os
import datetime
import operator

import pytest

from doit import exceptions
from doit import tools
from doit import task


def test_create_folder():
    def rm_dir():
        if os.path.exists(DIR_DEP):
            os.removedirs(DIR_DEP)

    DIR_DEP = os.path.join(os.path.dirname(__file__),"parent/child/")
    rm_dir()
    assert True == tools.create_folder(DIR_DEP)
    assert os.path.exists(DIR_DEP)
    rm_dir()


class TestTitleWithActions(object):
    def test_actions(self):
        t = task.Task("MyName",["MyAction"], title=tools.title_with_actions)
        assert "MyName => Cmd: MyAction" == t.title()

    def test_group(self):
        t = task.Task("MyName", None, file_dep=['file_foo'],
                      task_dep=['t1','t2'], title=tools.title_with_actions)
        assert "MyName => Group: t1, t2" == t.title()


class TestRunOnce(object):
    def test_run(self):
        t = task.Task("TaskX", None, uptodate=[tools.run_once])
        assert False == tools.run_once(t, t.values)
        t.save_extra_values()
        assert True == tools.run_once(t, t.values)


class TestResultDep(object):
    def test_single(self, depfile):
        dep_manager = depfile

        tasks = {'t1': task.Task("t1", None, uptodate=[tools.result_dep('t2')]),
                 't2': task.Task("t2", None),
                 }
        # _config_task was executed and t2 added as task_dep
        assert ['t2'] == tasks['t1'].task_dep

        # first t2 result
        tasks['t2'].result = 'yes'
        dep_manager.save_success(tasks['t2'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks)  # first time

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks)

        # t2 result changed
        tasks['t2'].result = '222'
        dep_manager.save_success(tasks['t2'])

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks)

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks)


    def test_group(self, depfile):
        dep_manager = depfile

        tasks = {'t1': task.Task("t1", None, uptodate=[tools.result_dep('t2')]),
                 't2': task.Task("t2", None, task_dep=['t2:a', 't2:b'],
                                 has_subtask=True),
                 't2:a': task.Task("t2:a", None),
                 't2:b': task.Task("t2:b", None),
                 }
        # _config_task was executed and t2 added as task_dep
        assert ['t2'] == tasks['t1'].task_dep

        # first t2 result
        tasks['t2:a'].result = 'yes1'
        dep_manager.save_success(tasks['t2:a'])
        tasks['t2:b'].result = 'yes2'
        dep_manager.save_success(tasks['t2:b'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks)  # first time

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks)

        # t2 result changed
        tasks['t2:a'].result = '222'
        dep_manager.save_success(tasks['t2:a'])

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks)

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks)



class TestConfigChanged(object):
    def test_invalid_type(self):
        class NotValid(object):pass
        uptodate = tools.config_changed(NotValid())
        pytest.raises(Exception, uptodate, None, None)

    def test_string(self):
        ua = tools.config_changed('a')
        ub = tools.config_changed('b')
        t1 = task.Task("TaskX", None, uptodate=[ua])
        assert False == ua(t1, t1.values)
        assert False == ub(t1, t1.values)
        t1.save_extra_values()
        assert True == ua(t1, t1.values)
        assert False == ub(t1, t1.values)

    def test_unicode(self):
        ua = tools.config_changed({'x':u"中文"})
        ub = tools.config_changed('b')
        t1 = task.Task("TaskX", None, uptodate=[ua])
        assert False == ua(t1, t1.values)
        assert False == ub(t1, t1.values)
        t1.save_extra_values()
        assert True == ua(t1, t1.values)
        assert False == ub(t1, t1.values)

    def test_dict(self):
        ua = tools.config_changed({'x':'a', 'y':1})
        ub = tools.config_changed({'x':'b', 'y':1})
        t1 = task.Task("TaskX", None, uptodate=[ua])
        assert False == ua(t1, t1.values)
        assert False == ub(t1, t1.values)
        t1.save_extra_values()
        assert True == ua(t1, t1.values)
        assert False == ub(t1, t1.values)


class TestTimeout(object):
    def test_invalid(self):
        pytest.raises(Exception, tools.timeout, "abc")

    def test_int(self, monkeypatch):
        monkeypatch.setattr(tools.time_module, 'time', lambda: 100)
        uptodate = tools.timeout(5)
        t = task.Task("TaskX", None, uptodate=[uptodate])

        assert False == uptodate(t, t.values)
        t.save_extra_values()
        assert 100 == t.values['success-time']

        monkeypatch.setattr(tools.time_module, 'time', lambda: 103)
        assert True == uptodate(t, t.values)

        monkeypatch.setattr(tools.time_module, 'time', lambda: 106)
        assert False == uptodate(t, t.values)


    def test_timedelta(self, monkeypatch):
        monkeypatch.setattr(tools.time_module, 'time', lambda: 10)
        limit = datetime.timedelta(minutes=2)
        uptodate = tools.timeout(limit)
        t = task.Task("TaskX", None, uptodate=[uptodate])

        assert False == uptodate(t, t.values)
        t.save_extra_values()
        assert 10 == t.values['success-time']

        monkeypatch.setattr(tools.time_module, 'time', lambda: 100)
        assert True == uptodate(t, t.values)

        monkeypatch.setattr(tools.time_module, 'time', lambda: 200)
        assert False == uptodate(t, t.values)


    def test_timedelta_big(self, monkeypatch):
        monkeypatch.setattr(tools.time_module, 'time', lambda: 10)
        limit = datetime.timedelta(days=2, minutes=5)
        uptodate = tools.timeout(limit)
        t = task.Task("TaskX", None, uptodate=[uptodate])

        assert False == uptodate(t, t.values)
        t.save_extra_values()
        assert 10 == t.values['success-time']

        monkeypatch.setattr(tools.time_module, 'time', lambda: 3600 * 30)
        assert True == uptodate(t, t.values)

        monkeypatch.setattr(tools.time_module, 'time', lambda: 3600 * 49)
        assert False == uptodate(t, t.values)


@pytest.fixture
def checked_file(request):
    fname = 'mytmpfile'
    file_ = open(fname, 'a')
    file_.close()
    def remove():
        os.remove(fname)
    request.addfinalizer(remove)
    return fname


class TestCheckTimestampUnchanged(object):

    def test_time_selection(self):
        check = tools.check_timestamp_unchanged('check_atime', 'atime')
        assert 'st_atime' == check._timeattr

        check = tools.check_timestamp_unchanged('check_ctime', 'ctime')
        assert 'st_ctime' == check._timeattr

        check = tools.check_timestamp_unchanged('check_mtime', 'mtime')
        assert 'st_mtime' == check._timeattr

        pytest.raises(
            ValueError,
            tools.check_timestamp_unchanged, 'check_invalid_time', 'foo')

    def test_file_missing(self):
        check = tools.check_timestamp_unchanged('no_such_file')
        t = task.Task("TaskX", None, uptodate=[check])
        # fake values saved from previous run
        task_values = {check._key: 1} # needs any value different from None
        pytest.raises(OSError, check, t, task_values)

    def test_op_ge(self, monkeypatch, checked_file):
        check = tools.check_timestamp_unchanged(checked_file,cmp_op=operator.ge)
        t = task.Task("TaskX", None, uptodate=[check])

        # no stored value/first run
        assert False == check(t, t.values)

        # value just stored is equal to itself
        t.save_extra_values()
        assert True == check(t, t.values)

        # stored timestamp less than current, up to date
        future_time = t.values.values()[0] + 100
        monkeypatch.setattr(check, '_get_time', lambda: future_time)
        assert False == check(t, t.values)


    def test_op_bad_custom(self, monkeypatch, checked_file):
        # handling misbehaving custom operators
        def bad_op(prev_time, current_time):
            raise Exception('oops')

        check = tools.check_timestamp_unchanged(checked_file, cmp_op=bad_op)
        t = task.Task("TaskX", None, uptodate=[check])
        # fake values saved from previous run
        task_values = {check._key: 1} # needs any value different from None
        pytest.raises(Exception, check, t, task_values)

    def test_multiple_checks(self):
        # handling multiple checks on one file (should save values in such way
        # they don't override each other)
        check_a = tools.check_timestamp_unchanged('check_multi', 'atime')
        check_m = tools.check_timestamp_unchanged('check_multi', 'mtime')
        assert check_a._key != check_m._key


class TestInteractiveAction(object):
    def test_success(self):
        TEST_PATH = os.path.dirname(__file__)
        PROGRAM = "python %s/sample_process.py" % TEST_PATH
        my_action = tools.InteractiveAction(PROGRAM + " please fail")
        got = my_action.execute()
        assert got is None

    def test_ignore_keyboard_interrupt(self, monkeypatch):
        my_action = tools.InteractiveAction('')
        class FakeRaiseInterruptProcess(object):
            def __init__(self, *args, **kwargs):
                pass
            def wait(self):
                raise KeyboardInterrupt()
        monkeypatch.setattr(tools.subprocess, 'Popen', FakeRaiseInterruptProcess)
        got = my_action.execute()
        assert got is None


class TestPythonInteractiveAction(object):
    def test_success(self):
        def hello(): print('hello')
        my_action = tools.PythonInteractiveAction(hello)
        got = my_action.execute()
        assert got is None

    def test_ignore_keyboard_interrupt(self, monkeypatch):
        def raise_x(): raise Exception('x')
        my_action = tools.PythonInteractiveAction(raise_x)
        got = my_action.execute()
        assert isinstance(got, exceptions.TaskError)


