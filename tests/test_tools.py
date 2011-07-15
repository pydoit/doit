import os
import datetime

import pytest

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
        t.execute()
        assert True == tools.run_once(t, t.values)


class TestConfigChanged(object):\

    def test_invalid_type(self):
        class NotValid(object):pass
        pytest.raises(Exception, tools.config_changed, NotValid())

    def test_string(self):
        ua = tools.config_changed('a')
        ub = tools.config_changed('b')
        t1 = task.Task("TaskX", None, uptodate=[ua])
        assert False == ua(t1, t1.values)
        assert False == ub(t1, t1.values)
        t1.execute()
        assert True == ua(t1, t1.values)
        assert False == ub(t1, t1.values)

    def test_dict(self):
        ua = tools.config_changed({'x':'a', 'y':1})
        ub = tools.config_changed({'x':'b', 'y':1})
        t1 = task.Task("TaskX", None, uptodate=[ua])
        assert False == ua(t1, t1.values)
        assert False == ub(t1, t1.values)
        t1.execute()
        assert True == ua(t1, t1.values)
        assert False == ub(t1, t1.values)


class TestTimeout(object):
    def test_invalid(self):
        pytest.raises(Exception, tools.timeout, "abc")

    def test_int(self, monkeypatch):
        monkeypatch.setattr(tools.time, 'time', lambda: 100)
        t = task.Task("TaskX", None, uptodate=[tools.timeout(5)])

        assert False == t.uptodate[0](t, t.values)
        t.execute()
        assert 100 == t.values['success-time']

        monkeypatch.setattr(tools.time, 'time', lambda: 103)
        assert True == t.uptodate[0](t, t.values)

        monkeypatch.setattr(tools.time, 'time', lambda: 106)
        assert False == t.uptodate[0](t, t.values)


    def test_timedelta(self, monkeypatch):
        monkeypatch.setattr(tools.time, 'time', lambda: 10)
        limit = datetime.timedelta(minutes=2)
        t = task.Task("TaskX", None, uptodate=[tools.timeout(limit)])

        assert False == t.uptodate[0](t, t.values)
        t.execute()
        assert 10 == t.values['success-time']

        monkeypatch.setattr(tools.time, 'time', lambda: 100)
        assert True == t.uptodate[0](t, t.values)

        monkeypatch.setattr(tools.time, 'time', lambda: 200)
        assert False == t.uptodate[0](t, t.values)


    def test_timedelta_big(self, monkeypatch):
        monkeypatch.setattr(tools.time, 'time', lambda: 10)
        limit = datetime.timedelta(days=2, minutes=5)
        t = task.Task("TaskX", None, uptodate=[tools.timeout(limit)])

        assert False == t.uptodate[0](t, t.values)
        t.execute()
        assert 10 == t.values['success-time']

        monkeypatch.setattr(tools.time, 'time', lambda: 3600 * 30)
        assert True == t.uptodate[0](t, t.values)

        monkeypatch.setattr(tools.time, 'time', lambda: 3600 * 49)
        assert False == t.uptodate[0](t, t.values)
