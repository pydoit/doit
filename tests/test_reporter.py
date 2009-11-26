import sys
import StringIO

from doit import reporter
from doit.task import Task
from doit import CatchedException
from doit.dependency import json #FIXME move json import to __init__.py


class TestConsoleReporter(object):
    def setUp(self):
        self.output = StringIO.StringIO()
        self.rep = reporter.ConsoleReporter(self.output, True, True)
        self.my_task = Task("t_name", None)

    def test_startTask(self):
        self.rep.start_task(self.my_task)
        # no output on start task
        assert "" in self.output.getvalue()

    def test_executeTask(self):
        def do_nothing():pass
        t1 = Task("with_action",[(do_nothing,)])
        self.rep.execute_task(t1)
        assert "with_action" in self.output.getvalue()

    def test_executeGroupTask(self):
        self.rep.execute_task(self.my_task)
        assert "" == self.output.getvalue()

    def test_skipUptodate(self):
        self.rep.skip_uptodate(self.my_task)
        assert "---" in self.output.getvalue()
        assert "t_name" in self.output.getvalue()

    def test_skipIgnore(self):
        self.rep.skip_ignore(self.my_task)
        assert "!!!" in self.output.getvalue()
        assert "t_name" in self.output.getvalue()


    def test_cleanupError(self):
        oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            exception = CatchedException("I got you")
            self.rep.cleanup_error(exception)
            assert "I got you" in sys.stderr.getvalue()
        finally:
            sys.stderr.close()
            sys.stderr = oldErr


    def test_addFailure(self):
        try:
            raise Exception("original exception message here")
        except Exception,e:
            catched = CatchedException("catched exception there", e)
        self.rep.add_failure(self.my_task, catched)
        self.rep.complete_run()
        got = self.output.getvalue()
        # description
        assert "Exception: original exception message here" in got, got
        # traceback
        assert """raise Exception("original exception message here")""" in got
        # catched message
        assert "catched exception there" in got


class TestExecutedOnlyReporter(object):
    def setUp(self):
        self.output = StringIO.StringIO()
        self.rep = reporter.ExecutedOnlyReporter(self.output, True, True)
        self.my_task = Task("t_name", None)

    def test_skipUptodate(self):
        self.rep.skip_uptodate(self.my_task)
        assert "" == self.output.getvalue()

    def test_skipIgnore(self):
        self.rep.skip_ignore(self.my_task)
        assert "" == self.output.getvalue()



class TestTaskResult(object):
    def test(self):
        def sample():
            print "this is printed"
        t1 = Task("t1", [(sample,)])
        result = reporter.TaskResult(t1)
        result.start()
        t1.execute()
        result.set_result('success')
        got = result.to_dict()
        assert t1.name == got['name'], got
        assert 'success' == got['result'], got
        assert "this is printed\n" == got['out'], got
        assert "" == got['err'], got
        assert got['started']
        assert got['elapsed']


class TestJsonReporter(object):

    def test(self):
        output = StringIO.StringIO()
        rep = reporter.JsonReporter(output)
        t1 = Task("t1", None)
        t2 = Task("t2", None)
        t3 = Task("t3", None)
        t4 = Task("t4", None)
        expected = {'t1':'fail', 't2':'up-to-date',
                    't3':'success', 't4':'ignore'}
        # t1 fail
        rep.start_task(t1)
        rep.execute_task(t1)
        rep.add_failure(t1, Exception('hi'))
        # t2 skipped
        rep.start_task(t2)
        rep.skip_uptodate(t2)
        # t3 success
        rep.start_task(t3)
        rep.execute_task(t3)
        rep.add_success(t3)
        # t4 ignore
        rep.start_task(t4)
        rep.skip_ignore(t4)

        rep.complete_run()
        got = json.loads(output.getvalue())
        for task_result in got['tasks']:
            assert expected[task_result['name']] == task_result['result'], got

        # just ignore this
        rep.cleanup_error(Exception('xx'))


    def test_ignore_stdout(self):
        output = StringIO.StringIO()
        rep = reporter.JsonReporter(output)
        sys.stdout.write("info that doesnt belong to any task...")
        sys.stderr.write('something on err')
        t1 = Task("t1", None)
        expected = {'t1':'success'}
        rep.start_task(t1)
        rep.execute_task(t1)
        rep.add_success(t1)
        rep.complete_run()
        got = json.loads(output.getvalue())
        assert expected[got['tasks'][0]['name']] == got['tasks'][0]['result']
        assert "info that doesnt belong to any task..." == got['out']
        assert "something on err" == got['err']
