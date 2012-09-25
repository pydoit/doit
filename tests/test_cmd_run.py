import StringIO
import os

import pytest
from mock import Mock

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit import reporter, runner
from doit.cmd_run import Run
doit_run = Run._execute
from tests.conftest import tasks_sample


class TestCmdRun(object):

    def testProcessRun(self, depfile):
        output = StringIO.StringIO()
        result = doit_run(depfile.name, tasks_sample(), output)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testMP_not_available(self, depfile, monkeypatch):
        # make sure MRunner wont be used
        monkeypatch.setattr(runner.MRunner, "available",
                            Mock(return_value=False))
        monkeypatch.setattr(runner.MRunner, "__init__", 'not available')
        output = StringIO.StringIO()
        doit_run(depfile.name, tasks_sample(), output, num_process=3)

    def testProcessRunMP(self, depfile):
        output = StringIO.StringIO()
        result = doit_run(depfile.name, tasks_sample(), output, num_process=1)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunFilter(self, depfile):
        output = StringIO.StringIO()
        doit_run(depfile.name, tasks_sample(), output, ["g1.a"])
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got, repr(got)

    def testProcessRunEmptyFilter(self, depfile):
        output = StringIO.StringIO()
        doit_run(depfile.name, tasks_sample(), output, [])
        got = output.getvalue().split("\n")[:-1]
        assert [] == got

    def testInvalidReporter(self, depfile):
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, doit_run,
                depfile.name, tasks_sample(), output, reporter="i dont exist")

    def testCustomReporter(self, depfile):
        output = StringIO.StringIO()
        class MyReporter(reporter.ConsoleReporter):
            def get_status(self, task):
                self.outstream.write('MyReporter.start %s\n' % task.name)
        doit_run(depfile.name, [tasks_sample()[0]], output, reporter=MyReporter)
        got = output.getvalue().split("\n")[:-1]
        assert 'MyReporter.start t1' == got[0]

    def testSetVerbosity(self, depfile):
        output = StringIO.StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        doit_run(depfile.name, [t], output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity

    def test_outfile(self, depfile):
        doit_run(depfile.name, tasks_sample(), 'test.out', ["g1.a"])
        try:
            outfile = open('test.out', 'r')
            got = outfile.read()
            outfile.close()
            assert ".  g1.a\n" == got, repr(got)
        finally:
            if os.path.exists('test.out'):
                os.remove('test.out')


