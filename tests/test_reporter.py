import sys
import json
from io import StringIO

from doit import reporter
from doit.task import Stream, Task
from doit.exceptions import CatchedException


class TestConsoleReporter(object):

    def test_initialize(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.initialize([Task("t_name", None)], ["t_name"])
        # no output on initialize
        assert "" in rep.outstream.getvalue()

    def test_startTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.get_status(Task("t_name", None))
        # no output on start task
        assert "" in rep.outstream.getvalue()

    def test_executeTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("with_action",[(do_nothing,)])
        rep.execute_task(t1)
        assert ".  with_action\n" == rep.outstream.getvalue()

    def test_executeTask_unicode(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        task_name = "中文 with_action"
        t1 = Task(task_name, [(do_nothing,)])
        rep.execute_task(t1)
        assert ".  中文 with_action\n" == rep.outstream.getvalue()


    def test_executeHidden(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("_hidden",[(do_nothing,)])
        rep.execute_task(t1)
        assert "" == rep.outstream.getvalue()

    def test_executeGroupTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.execute_task(Task("t_name", None))
        assert "" == rep.outstream.getvalue()

    def test_skipUptodate(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_uptodate(Task("t_name", None))
        assert "-- " in rep.outstream.getvalue()
        assert "t_name" in rep.outstream.getvalue()

    def test_skipUptodate_hidden(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_uptodate(Task("_name", None))
        assert "" == rep.outstream.getvalue()

    def test_skipIgnore(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.skip_ignore(Task("t_name", None))
        assert "!! " in rep.outstream.getvalue()
        assert "t_name" in rep.outstream.getvalue()


    def test_cleanupError(self, capsys):
        rep = reporter.ConsoleReporter(StringIO(), {})
        exception = CatchedException("I got you")
        rep.cleanup_error(exception)
        err = capsys.readouterr()[1]
        assert "I got you" in err

    def test_teardownTask(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.teardown_task(Task("t_name", None))
        # no output on teardown task
        assert "" in rep.outstream.getvalue()

    def test_addSuccess(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        rep.add_success(Task("t_name", None))
        # no output on success task
        assert "" in rep.outstream.getvalue()

    def test_addFailure(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        try:
            raise Exception("original 中文 exception message here")
        except Exception as e:
            catched = CatchedException("catched exception there", e)
        rep.add_failure(Task("t_name", None, verbosity=1), catched)
        rep.complete_run()
        got = rep.outstream.getvalue()
        # description
        assert "Exception: original 中文 exception message here" in got, got
        # traceback
        assert """raise Exception("original 中文 exception message here")""" in got
        # catched message
        assert "catched exception there" in got

    def test_runtime_error(self):
        msg = "runtime error"
        rep = reporter.ConsoleReporter(StringIO(), {})
        assert [] == rep.runtime_errors
        # no imediate output
        rep.runtime_error(msg)
        assert 1 == len(rep.runtime_errors)
        assert msg == rep.runtime_errors[0]
        assert "" in rep.outstream.getvalue()
        # runtime errors abort execution
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert msg in got
        assert "Execution aborted" in got


    def test_complete_run_verbosity0(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        catched = CatchedException("catched exception there",
                                   Exception("foo"))

        task = Task("t_name", None, verbosity=0)
        task.executed = True
        rep.add_failure(task, catched)

        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert "<stdout>" in got
        assert "<stderr>" in got

    def test_complete_run_verbosity0_not_executed(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        catched = CatchedException("catched exception there",
                                   Exception("foo"))

        task = Task("t_name", None, verbosity=0)
        task.executed = False
        rep.add_failure(task, catched)

        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert "<stdout>" not in got
        assert "<stderr>" not in got

    def test_complete_run_verbosity1(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        catched = CatchedException("catched exception there",
                                   Exception("foo"))

        task = Task("t_name", None, verbosity=1)
        task.executed = True
        rep.add_failure(task, catched)

        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert "<stdout>" in got
        assert "<stderr>" not in got

    def test_complete_run_verbosity2(self):
        rep = reporter.ConsoleReporter(StringIO(), {})
        catched = CatchedException("catched exception there",
                                   Exception("foo"))

        rep.add_failure(Task("t_name", None, verbosity=2), catched)

        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert "<stdout>" not in got
        assert "<stderr>" not in got


    def test_complete_run_verbosity2_redisplay(self):
        rep = reporter.ConsoleReporter(StringIO(), {'failure_verbosity': 2})
        catched = CatchedException("catched exception there",
                                   Exception("foo"))

        task = Task("t_name", None, verbosity=2)
        task.executed = True
        rep.add_failure(task, catched)

        # assign new StringIO so output is only from complete_run()
        rep.outstream = StringIO()
        rep.complete_run()
        got = rep.outstream.getvalue()
        assert "<stdout>" in got
        assert "<stderr>" in got



class TestExecutedOnlyReporter(object):
    def test_skipUptodate(self):
        rep = reporter.ExecutedOnlyReporter(StringIO(), {})
        rep.skip_uptodate(Task("t_name", None))
        assert "" == rep.outstream.getvalue()

    def test_skipIgnore(self):
        rep = reporter.ExecutedOnlyReporter(StringIO(), {})
        rep.skip_ignore(Task("t_name", None))
        assert "" == rep.outstream.getvalue()


class TestZeroReporter(object):
    def test_executeTask(self):
        rep = reporter.ZeroReporter(StringIO(), {})
        def do_nothing():pass
        t1 = Task("with_action",[(do_nothing,)])
        rep.execute_task(t1)
        assert "" == rep.outstream.getvalue()

    def test_runtime_error(self, capsys):
        msg = "zero runtime error"
        rep = reporter.ZeroReporter(StringIO(), {})
        # imediate output
        rep.runtime_error(msg)
        assert msg in capsys.readouterr()[1]


class TestTaskResult(object):
    def test(self):
        def sample():
            print("this is printed")
        t1 = Task("t1", [(sample,)])
        result = reporter.TaskResult(t1)
        result.start()
        t1.execute(Stream(0))
        result.set_result('success')
        got = result.to_dict()
        assert t1.name == got['name'], got
        assert 'success' == got['result'], got
        assert "this is printed\n" == got['out'], got
        assert "" == got['err'], got
        assert got['started']
        assert 'elapsed' in got


class TestJsonReporter(object):

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
        rep.add_failure(t1, CatchedException('t1 failed!'))
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
            assert expected[task_result['name']] == task_result['result'], got
            if task_result['name'] == 't1':
                assert 't1 failed!' in task_result['error']

    def test_cleanup_error(self, capsys):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        msg = "cleanup error"
        exception = CatchedException(msg)
        assert [] == rep.errors
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        rep.cleanup_error(exception)
        assert [msg+'\n'] == rep.errors
        assert "" in rep.outstream.getvalue()
        rep.complete_run()
        got = json.loads(output.getvalue())
        assert msg in got['err']

    def test_runtime_error(self):
        output = StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        msg = "runtime error"
        assert [] == rep.errors
        rep.get_status(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        rep.runtime_error(msg)
        assert [msg] == rep.errors
        assert "" in rep.outstream.getvalue()
        # runtime errors abort execution
        rep.complete_run()
        got = json.loads(output.getvalue())
        assert msg in got['err']

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
        assert expected[got['tasks'][0]['name']] == got['tasks'][0]['result']
        assert "info that doesnt belong to any task..." == got['out']
        assert "something on err" == got['err']
