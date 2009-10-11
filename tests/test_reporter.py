import sys
import StringIO

from doit.reporter import ConsoleReporter
from doit.task import Task
from doit import CatchedException


class BaseTestOutput(object):
    """base class for tests that use stdout"""
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut
        sys.stderr.close()
        sys.stderr = self.oldErr


class TestConsoleReporter(BaseTestOutput):
    def setUp(self):
        BaseTestOutput.setUp(self)
        self.rep = ConsoleReporter(True, True)
        self.my_task = Task("t_name", None)

    def test_startTask(self):
        self.rep.start_task(self.my_task)
        assert "t_name" in sys.stdout.getvalue()

    def test_skipUptodate(self):
        self.rep.skip_uptodate(self.my_task)
        assert "---" in sys.stdout.getvalue()
        assert "t_name" in sys.stdout.getvalue()


    def test_cleanupError(self):
        exception = CatchedException("I got you")
        self.rep.cleanup_error(exception)
        assert "I got you" in sys.stderr.getvalue()

    def test_addFailure(self):
        try:
            raise Exception("original exception message here")
        except Exception,e:
            catched = CatchedException("catched exception there", e)
        self.rep.add_failure(self.my_task, catched)
        self.rep.complete_run()
        got = sys.stderr.getvalue()
        # description
        assert "Exception: original exception message here" in got, got
        # traceback
        assert """raise Exception("original exception message here")""" in got
        # catched message
        assert "catched exception there" in got
