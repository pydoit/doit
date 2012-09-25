import StringIO
import os

import pytest
from mock import Mock

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit import reporter, runner
from doit.cmd_run import Run
from tests.conftest import tasks_sample


class TestCmdRun(object):

    def testProcessRun(self, depfile):
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample())
        result = cmd_run._execute(output)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testMP_not_available(self, depfile, monkeypatch):
        # make sure MRunner wont be used
        monkeypatch.setattr(runner.MRunner, "available",
                            Mock(return_value=False))
        monkeypatch.setattr(runner.MRunner, "__init__", 'not available')
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample())
        cmd_run._execute(output, num_process=3)

    def testProcessRunMP(self, depfile):
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample())
        result = cmd_run._execute(output, num_process=1)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunFilter(self, depfile):
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample(),
                      sel_tasks=["g1.a"])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got, repr(got)

    def testProcessRunEmptyFilter(self, depfile):
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample(),
                      sel_tasks=[])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        assert [] == got

    def testInvalidReporter(self, depfile):
        output = StringIO.StringIO()
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_run._execute,
                      output, reporter="i dont exist")

    def testCustomReporter(self, depfile):
        output = StringIO.StringIO()
        class MyReporter(reporter.ConsoleReporter):
            def get_status(self, task):
                self.outstream.write('MyReporter.start %s\n' % task.name)
        cmd_run = Run(dep_file=depfile.name, task_list=[tasks_sample()[0]])
        cmd_run._execute(output, reporter=MyReporter)
        got = output.getvalue().split("\n")[:-1]
        assert 'MyReporter.start t1' == got[0]

    def testSetVerbosity(self, depfile):
        output = StringIO.StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        cmd_run = Run(dep_file=depfile.name, task_list=[t])
        cmd_run._execute(output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity

    def test_outfile(self, depfile):
        cmd_run = Run(dep_file=depfile.name, task_list=tasks_sample(),
                      sel_tasks=["g1.a"])
        cmd_run._execute('test.out')
        try:
            outfile = open('test.out', 'r')
            got = outfile.read()
            outfile.close()
            assert ".  g1.a\n" == got, repr(got)
        finally:
            if os.path.exists('test.out'):
                os.remove('test.out')


