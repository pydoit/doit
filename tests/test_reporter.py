import io
import sys
import json
import unittest
import contextlib
from io import StringIO

from doit import reporter
from doit.task import Stream, Task
from doit.exceptions import BaseFail, TaskFailed


class TestConsoleReporter(unittest.TestCase):

    def test_initialize(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.initialize([Task("t_name", None)], ["t_name"])
        # no output on initialize
        self.assertIn("", rep.outstream.getvalue())

    def test_startTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.get_status(Task("t_name", None))
        # no output on start task
        self.assertIn("", rep.outstream.getvalue())

    def test_executeTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("with_action",[(do_nothing,)])
        rep.execute_task(t1)
        self.assertEqual(".  with_action\n", rep.outstream.getvalue())

    def test_executeTask_unicode(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        task_name = "中文 with_action"
        t1 = Task(task_name, [(do_nothing,)])
        rep.execute_task(t1)
        self.assertEqual(".  中文 with_action\n", rep.outstream.getvalue())

    def test_executeHidden(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("_hidden",[(do_nothing,)])
        rep.execute_task(t1)
        self.assertEqual("", rep.outstream.getvalue())

    def test_executeGroupTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.execute_task(Task("t_name", None))
        self.assertEqual("", rep.outstream.getvalue())

    def test_skipUptodate(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_uptodate(Task("t_name", None))
        self.assertIn("-- ", rep.outstream.getvalue())
        self.assertIn("t_name", rep.outstream.getvalue())

    def test_skipUptodate_hidden(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_uptodate(Task("_name", None))
        self.assertEqual("", rep.outstream.getvalue())

    def test_skipIgnore(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_ignore(Task("t_name", None))
        self.assertIn("!! ", rep.outstream.getvalue())
        self.assertIn("t_name", rep.outstream.getvalue())

    def test_cleanupError(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        fail = TaskFailed("I got you")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rep.cleanup_error(fail)
        self.assertIn("I got you", err.getvalue())

    def test_teardownTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.teardown_task(Task("t_name", None))
        # no output on teardown task
        self.assertIn("", rep.outstream.getvalue())

    def test_addSuccess(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.add_success(Task("t_name", None))
        # no output on success task
        self.assertIn("", rep.outstream.getvalue())

    def test_addFailure(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        try:
            raise Exception("original 中文 exception message here")
        except Exception as e:
            caught = TaskFailed("caught exception there", e)
        rep.add_failure(Task("t_name", None, verbosity=1), caught)
        rep.complete_run()
        got = rep.outstream.getvalue()
        # description
        self.assertIn("Exception: original 中文 exception message here", got)
        # traceback
        self.assertIn('raise Exception("original 中文 exception message here")', got)
        # caught message
        self.assertIn("caught exception there", got)

    def test_failure_no_report(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        failure = TaskFailed("caught exception there", Exception("ExceptionKind"), report=False)
        rep.add_failure(Task("t_name", None, verbosity=1), failure)
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertNotIn("ExceptionKind", got)
        self.assertNotIn("caught exception there", got)

    def test_runtime_error(self):
        msg = "runtime error"
        rep = reporter.ConsoleReporter(StringIO(), {})
        self.assertEqual([], rep.runtime_errors)
        # no imediate output
        rep.runtime_error(msg)
        self.assertEqual(1, len(rep.runtime_errors))
        self.assertEqual(msg, rep.runtime_errors[0])
        self.assertIn("", rep.outstream.getvalue())
        # runtime errors abort execution
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertIn(msg, got)
        self.assertIn("Execution aborted", got)

    def test_complete_run_verbosity0(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        caught = TaskFailed("caught exception there", Exception("foo"))
        task = Task("t_name", None, verbosity=0)
        task.executed = True
        rep.add_failure(task, caught)
        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertIn("<stdout>", got)
        self.assertIn("<stderr>", got)

    def test_complete_run_verbosity0_not_executed(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        caught = TaskFailed("caught exception there", Exception("foo"))
        task = Task("t_name", None, verbosity=0)
        task.executed = False
        rep.add_failure(task, caught)
        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertNotIn("<stdout>", got)
        self.assertNotIn("<stderr>", got)

    def test_complete_run_verbosity1(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        caught = TaskFailed("caught exception there", Exception("foo"))
        task = Task("t_name", None, verbosity=1)
        task.executed = True
        rep.add_failure(task, caught)
        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertIn("<stdout>", got)
        self.assertNotIn("<stderr>", got)

    def test_complete_run_verbosity2(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        caught = TaskFailed("caught exception there", Exception("foo"))
        rep.add_failure(Task("t_name", None, verbosity=2), caught)
        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertNotIn("<stdout>", got)
        self.assertNotIn("<stderr>", got)

    def test_complete_run_verbosity2_redisplay(self):
        rep = reporter.ConsoleReporter(StringIO(), {'failure_verbosity': 2})
        caught = TaskFailed("caught exception there", Exception("foo"))
        task = Task("t_name", None, verbosity=2)
        task.executed = True
        rep.add_failure(task, caught)
        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        self.assertIn("<stdout>", got)
        self.assertIn("<stderr>", got)


class TestExecutedOnlyReporter(unittest.TestCase):
    def test_skipUptodate(self):
        rep = reporter.ExecutedOnlyReporter(StringIO(), {})
        rep.skip_uptodate(Task("t_name", None))
        self.assertEqual("", rep.outstream.getvalue())

    def test_skipIgnore(self):
        rep = reporter.ExecutedOnlyReporter(StringIO(), {})
        rep.skip_ignore(Task("t_name", None))
        self.assertEqual("", rep.outstream.getvalue())


class TestZeroReporter(unittest.TestCase):
    def test_executeTask(self):
        rep = reporter.ZeroReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("with_action",[(do_nothing,)])
        rep.execute_task(t1)
        self.assertEqual("", rep.outstream.getvalue())

    def test_runtime_error(self):
        msg = "zero runtime error"
        rep = reporter.ZeroReporter(StringIO(), {})
        # imediate output
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rep.runtime_error(msg)
        self.assertIn(msg, err.getvalue())


class TestErrorOnlyReporter(unittest.TestCase):
    def test_executeTask(self):
        rep = reporter.ErrorOnlyReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("with_action", [(do_nothing,)])
        rep.execute_task(t1)
        self.assertEqual("", rep.outstream.getvalue())

    def test_faile_no_report(self):
        rep = reporter.ErrorOnlyReporter(StringIO(), {})
        failure = TaskFailed("An error here", report=False)
        rep.add_failure(Task("t_name", None, verbosity=1), failure)
        self.assertEqual("", rep.outstream.getvalue())

    def test_error_report(self):
        class UnknownException(BaseFail):
            pass
        rep = reporter.ErrorOnlyReporter(StringIO(), {})
        exception = Exception("Error message here")
        failure = UnknownException("Something unexpected", exception)
        rep.add_failure(Task("t_name", None, verbosity=1), failure)
        self.assertIn("Error message here", rep.outstream.getvalue())
        self.assertIn("Something unexpected", rep.outstream.getvalue())


class TestTaskResult(unittest.TestCase):
    def test(self):
        def sample():
            print("this is printed")
        t1 = Task("t1", [(sample,)])
        result = reporter.TaskResult(t1)
        result.start()
        t1.execute(Stream(0))
        result.set_result('success')
        got = result.to_dict()
        self.assertEqual(t1.name, got['name'])
        self.assertEqual('success', got['result'])
        self.assertEqual("this is printed\n", got['out'])
        self.assertEqual("", got['err'])
        self.assertTrue(got['started'])
        self.assertIn('elapsed', got)


class TestJsonReporter(unittest.TestCase):

    def test_normal(self):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        t2 = Task("t2", None)
        t3 = Task("t3", None)
        t4 = Task("t4", None)
        expected = {'t1':'fail', 't2':'up-to-date',
                    't3':'success', 't4':'ignore'}
        # t1 fail
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_failure(t1, TaskFailed('t1 failed!'))
        # t2 skipped
        rep.get_status(t2)
        rep.skip_uptodate(t2)
        # t3 success
        rep.get_status(t3)
        rep.execute_task(t3)
        rep.add_success(t3)
        # t4 ignore
        rep.get_status(t4)
        rep.skip_ignore(t4)
        rep.teardown_task(t4)
        rep.complete_run()
        got = json.loads(output.getvalue())
        for task_result in got['tasks']:
            self.assertEqual(expected[task_result['name']], task_result['result'])
            if task_result['name'] == 't1':
                self.assertIn('t1 failed!', task_result['error'])

    def test_cleanup_error(self):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        msg = "cleanup error"
        fail = TaskFailed(msg)
        self.assertEqual([], rep.errors)
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rep.cleanup_error(fail)
        self.assertEqual([msg+'\n'], rep.errors)
        self.assertIn("", rep.outstream.getvalue())
        rep.complete_run()
        got = json.loads(output.getvalue())
        self.assertIn(msg, got['err'])

    def test_runtime_error(self):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        msg = "runtime error"
        self.assertEqual([], rep.errors)
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        rep.runtime_error(msg)
        self.assertEqual([msg], rep.errors)
        self.assertIn("", rep.outstream.getvalue())
        # runtime errors abort execution
        rep.complete_run()
        got = json.loads(output.getvalue())
        self.assertIn(msg, got['err'])

    def test_ignore_stdout(self):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        sys.stdout.write("info that doesnt belong to any task...")
        sys.stderr.write('something on err')
        t1 = Task("t1", None)
        expected = {'t1':'success'}
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        rep.complete_run()
        got = json.loads(output.getvalue())
        self.assertEqual(expected[got['tasks'][0]['name']], got['tasks'][0]['result'])
        self.assertEqual("info that doesnt belong to any task...", got['out'])
        self.assertEqual("something on err", got['err'])
