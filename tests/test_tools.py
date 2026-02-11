import os
import datetime
import json
import operator
import unittest
from sys import executable
from unittest.mock import patch

from doit import exceptions
from doit import tools
from doit import task


class TestCreateFolder(unittest.TestCase):
    def test_create_folder(self):
        DIR_DEP = os.path.join(os.path.dirname(__file__), "..", "tests",
                               "parent", "child/")
        self.addCleanup(lambda: os.path.exists(DIR_DEP) and os.removedirs(DIR_DEP))
        if os.path.exists(DIR_DEP):
            os.removedirs(DIR_DEP)
        tools.create_folder(DIR_DEP)
        self.assertTrue(os.path.exists(DIR_DEP))

    def test_error_if_path_is_a_file(self):
        path = os.path.join(os.path.dirname(__file__), "..", "tests",
                            "test_create_folder")
        with open(path, 'w') as fp:
            fp.write('testing')
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        self.assertRaises(OSError, tools.create_folder, path)


class TestTitleWithActions(unittest.TestCase):
    def test_actions(self):
        t = task.Task("MyName", ["MyAction"], title=tools.title_with_actions)
        self.assertEqual("MyName => Cmd: MyAction", t.title())

    def test_group(self):
        t = task.Task("MyName", None, file_dep=['file_foo'],
                      task_dep=['t1', 't2'], title=tools.title_with_actions)
        self.assertEqual("MyName => Group: t1, t2", t.title())


class TestRunOnce(unittest.TestCase):
    def test_run(self):
        t = task.Task("TaskX", None, uptodate=[tools.run_once])
        self.assertFalse(tools.run_once(t, t.values))
        t.save_extra_values()
        self.assertTrue(tools.run_once(t, t.values))


class TestConfigChanged(unittest.TestCase):
    def test_invalid_type(self):
        class NotValid(object): pass
        uptodate = tools.config_changed(NotValid())
        self.assertRaises(Exception, uptodate, None, None)

    def test_string(self):
        ua = tools.config_changed('a')
        ub = tools.config_changed('b')
        t1 = task.Task("TaskX", None, uptodate=[ua])
        self.assertFalse(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))
        t1.save_extra_values()
        self.assertTrue(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))

    def test_unicode(self):
        ua = tools.config_changed({'x': "中文"})
        ub = tools.config_changed('b')
        t1 = task.Task("TaskX", None, uptodate=[ua])
        self.assertFalse(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))
        t1.save_extra_values()
        self.assertTrue(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))

    def test_dict(self):
        ua = tools.config_changed({'x': 'a', 'y': 1})
        ub = tools.config_changed({'x': 'b', 'y': 1})
        t1 = task.Task("TaskX", None, uptodate=[ua])
        self.assertFalse(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))
        t1.save_extra_values()
        self.assertTrue(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))

    def test_nested_dict(self):
        # actually both dictionaries contain same values
        # but nested dictionary keys are in a different order
        c1a = tools.config_changed({'x': 'a', 'y': {'one': 1, 'two': 2}})
        c1b = tools.config_changed({'y': {'two': 2, 'one': 1}, 'x': 'a'})
        t1 = task.Task("TaskX", None, uptodate=[c1a])
        self.assertFalse(c1a(t1, t1.values))
        t1.save_extra_values()
        self.assertTrue(c1a(t1, t1.values))
        self.assertTrue(c1b(t1, t1.values))

    def test_using_custom_encoder(self):
        class DatetimeJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime.datetime):
                    return o.isoformat()

        ua = tools.config_changed(
            {'a': datetime.datetime(2018, 12, 10, 10, 33, 55, 478421), 'b': 'bb'},
            encoder=DatetimeJSONEncoder)
        ub = tools.config_changed(
            {'a': datetime.datetime.now(), 'b': 'bb'},
            encoder=DatetimeJSONEncoder)
        t1 = task.Task("TaskX", None, uptodate=[ua])
        self.assertFalse(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))
        t1.save_extra_values()
        self.assertTrue(ua(t1, t1.values))
        self.assertFalse(ub(t1, t1.values))


class TestTimeout(unittest.TestCase):
    def test_invalid(self):
        self.assertRaises(Exception, tools.timeout, "abc")

    def test_int(self):
        with patch.object(tools.time_module, 'time', return_value=100):
            uptodate = tools.timeout(5)
            t = task.Task("TaskX", None, uptodate=[uptodate])
            self.assertFalse(uptodate(t, t.values))
            t.save_extra_values()
            self.assertEqual(100, t.values['success-time'])

        with patch.object(tools.time_module, 'time', return_value=103):
            self.assertTrue(uptodate(t, t.values))

        with patch.object(tools.time_module, 'time', return_value=106):
            self.assertFalse(uptodate(t, t.values))

    def test_timedelta(self):
        with patch.object(tools.time_module, 'time', return_value=10):
            limit = datetime.timedelta(minutes=2)
            uptodate = tools.timeout(limit)
            t = task.Task("TaskX", None, uptodate=[uptodate])
            self.assertFalse(uptodate(t, t.values))
            t.save_extra_values()
            self.assertEqual(10, t.values['success-time'])

        with patch.object(tools.time_module, 'time', return_value=100):
            self.assertTrue(uptodate(t, t.values))

        with patch.object(tools.time_module, 'time', return_value=200):
            self.assertFalse(uptodate(t, t.values))

    def test_timedelta_big(self):
        with patch.object(tools.time_module, 'time', return_value=10):
            limit = datetime.timedelta(days=2, minutes=5)
            uptodate = tools.timeout(limit)
            t = task.Task("TaskX", None, uptodate=[uptodate])
            self.assertFalse(uptodate(t, t.values))
            t.save_extra_values()
            self.assertEqual(10, t.values['success-time'])

        with patch.object(tools.time_module, 'time', return_value=3600 * 30):
            self.assertTrue(uptodate(t, t.values))

        with patch.object(tools.time_module, 'time', return_value=3600 * 49):
            self.assertFalse(uptodate(t, t.values))


class TestCheckTimestampUnchanged(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.checked_file = os.path.join(os.path.dirname(__file__),
                                         'mytmpfile_rut')
        open(self.checked_file, 'a').close()
        self.addCleanup(os.remove, self.checked_file)

    def test_time_selection(self):
        check = tools.check_timestamp_unchanged('check_atime', 'atime')
        self.assertEqual('st_atime', check._timeattr)

        check = tools.check_timestamp_unchanged('check_ctime', 'ctime')
        self.assertEqual('st_ctime', check._timeattr)

        check = tools.check_timestamp_unchanged('check_mtime', 'mtime')
        self.assertEqual('st_mtime', check._timeattr)

        self.assertRaises(
            ValueError,
            tools.check_timestamp_unchanged, 'check_invalid_time', 'foo')

    def test_file_missing(self):
        check = tools.check_timestamp_unchanged('no_such_file')
        t = task.Task("TaskX", None, uptodate=[check])
        # fake values saved from previous run
        task_values = {check._key: 1} # needs any value different from None
        self.assertRaises(OSError, check, t, task_values)

    def test_op_ge(self):
        check = tools.check_timestamp_unchanged(
            self.checked_file, cmp_op=operator.ge)
        t = task.Task("TaskX", None, uptodate=[check])

        # no stored value/first run
        self.assertFalse(check(t, t.values))

        # value just stored is equal to itself
        t.save_extra_values()
        self.assertTrue(check(t, t.values))

        # stored timestamp less than current, up to date
        future_time = list(t.values.values())[0] + 100
        with patch.object(check, '_get_time', return_value=future_time):
            self.assertFalse(check(t, t.values))

    def test_op_bad_custom(self):
        # handling misbehaving custom operators
        def bad_op(prev_time, current_time):
            raise Exception('oops')

        check = tools.check_timestamp_unchanged(
            self.checked_file, cmp_op=bad_op)
        t = task.Task("TaskX", None, uptodate=[check])
        # fake values saved from previous run
        task_values = {check._key: 1} # needs any value different from None
        self.assertRaises(Exception, check, t, task_values)

    def test_multiple_checks(self):
        # handling multiple checks on one file (should save values in such way
        # they don't override each other)
        check_a = tools.check_timestamp_unchanged('check_multi', 'atime')
        check_m = tools.check_timestamp_unchanged('check_multi', 'mtime')
        self.assertNotEqual(check_a._key, check_m._key)


class TestLongRunning(unittest.TestCase):
    def test_success(self):
        TEST_PATH = os.path.join(os.path.dirname(__file__), "..", "tests")
        PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)
        my_action = tools.LongRunning(PROGRAM + " please fail")
        got = my_action.execute()
        self.assertIsNone(got)

    def test_ignore_keyboard_interrupt(self):
        my_action = tools.LongRunning('')
        class FakeRaiseInterruptProcess(object):
            def __init__(self, *args, **kwargs):
                pass
            def wait(self):
                raise KeyboardInterrupt()
        with patch.object(tools.subprocess, 'Popen', FakeRaiseInterruptProcess):
            got = my_action.execute()
        self.assertIsNone(got)


class TestInteractive(unittest.TestCase):
    def test_fail(self):
        TEST_PATH = os.path.join(os.path.dirname(__file__), "..", "tests")
        PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)
        my_action = tools.Interactive(PROGRAM + " please fail")
        got = my_action.execute()
        self.assertIsInstance(got, exceptions.TaskFailed)

    def test_success(self):
        TEST_PATH = os.path.join(os.path.dirname(__file__), "..", "tests")
        PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)
        my_action = tools.Interactive(PROGRAM + " ok")
        got = my_action.execute()
        self.assertIsNone(got)


class TestPythonInteractiveAction(unittest.TestCase):
    def test_success(self):
        def hello(): print('hello')
        my_action = tools.PythonInteractiveAction(hello)
        got = my_action.execute()
        self.assertIsNone(got)

    def test_ignore_keyboard_interrupt(self):
        def raise_x(): raise Exception('x')
        my_action = tools.PythonInteractiveAction(raise_x)
        got = my_action.execute()
        self.assertIsInstance(got, exceptions.TaskError)

    def test_returned_dict_saved_result_values(self):
        def val(): return {'x': 3}
        my_action = tools.PythonInteractiveAction(val)
        got = my_action.execute()
        self.assertIsNone(got)
        self.assertEqual(my_action.result, {'x': 3})
        self.assertEqual(my_action.values, {'x': 3})

    def test_returned_string_saved_result(self):
        def val(): return 'hello'
        my_action = tools.PythonInteractiveAction(val)
        got = my_action.execute()
        self.assertIsNone(got)
        self.assertEqual(my_action.result, 'hello')
