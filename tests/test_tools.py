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
        uptodate = tools.config_changed(NotValid())
        pytest.raises(Exception, uptodate, None, None)

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


class TestCheckTimestampUnchanged(object):
    def patch_os_stat(self, monkeypatch, fake_path,
                      st_mode=33188, st_ino=402886990, st_dev=65024L,
                      st_nlink=1, st_uid=0, st_gid=0, st_size=0,
                      st_atime=1317297141, st_mtime=1317297140,
                      st_ctime=1317297141):
        """helper to patch os.stat for one specific path."""
        real_stat = os.stat

        def fake_stat(path):
            if path == fake_path:
                return os.stat_result((st_mode, st_ino, st_dev, st_nlink,
                                       st_uid, st_gid, st_size,
                                       st_atime, st_mtime, st_ctime))
            else:
                return real_stat(path)

        monkeypatch.setattr(os, 'stat', fake_stat)

    # @todo: maybe parametrize test_atime, test_ctime, test_mtime and
    #        test_op_custom?  a lot of repetition there

    def test_atime(self, monkeypatch):
        check = tools.check_timestamp_unchanged('check_atime', 'atime')
        self.patch_os_stat(monkeypatch, 'check_atime', st_atime=1317460678)
        t = task.Task("TaskX", None, uptodate=[check])

        # no stored value/first run
        assert False == check(t, t.values)

        # value just stored
        t.execute()
        assert True == check(t, t.values)

        # file has changed, should now re-execute
        monkeypatch.undo()
        self.patch_os_stat(monkeypatch, 'check_atime', st_atime=1317470015)
        assert False == check(t, t.values)

    def test_ctime(self, monkeypatch):
        check = tools.check_timestamp_unchanged('check_ctime', 'ctime')
        self.patch_os_stat(monkeypatch, 'check_ctime', st_ctime=1317460678)
        t = task.Task("TaskX", None, uptodate=[check])

        # no stored value/first run
        assert False == check(t, t.values)

        # value just stored
        t.execute()
        assert True == check(t, t.values)

        # file has changed, should now re-execute
        monkeypatch.undo()
        self.patch_os_stat(monkeypatch, 'check_ctime', st_ctime=1317470015)
        assert False == check(t, t.values)

    def test_mtime(self, monkeypatch):
        check = tools.check_timestamp_unchanged('check_mtime', 'mtime')
        self.patch_os_stat(monkeypatch, 'check_mtime', st_mtime=1317460678)
        t = task.Task("TaskX", None, uptodate=[check])

        # no stored value/first run
        assert False == check(t, t.values)

        # value just stored
        t.execute()
        assert True == check(t, t.values)

        # file has changed, should now re-execute
        monkeypatch.undo()
        self.patch_os_stat(monkeypatch, 'check_mtime', st_mtime=1317470015)
        assert False == check(t, t.values)

    def test_invalid_time(self):
        with pytest.raises(ValueError):
            tools.check_timestamp_unchanged('check_invalid_time', 'foo')

    def test_file_missing(self):
        # @todo: do we need to distinguish between file gone missing (e.g.
        #        prev_time is valid but current_time not) and the case where
        #        we never seen the file (neither prev_time nor current_time
        #        valid); the latter could e.g. be a typo by the user

        # no such file at all
        check = tools.check_timestamp_unchanged('no_such_file')
        t = task.Task("TaskX", None, uptodate=[check])
        assert False == check(t, t.values)

        # file gone missing
        self.patch_os_stat(monkeypatch, 'file_missing', st_ctime=1317460678)
        check = tools.check_timestamp_unchanged('file_missing')
        t = task.Task("TaskX", None, uptodate=[check])
        t.execute()
        assert True == check(t, t.values)
        monkeypatch.undo()
        assert False == check(t, t.values)

    def test_op_gt(self):
        pass

    def test_op_gt_file_missing(self):
        pass

    def test_op_custom(self):
        pass
