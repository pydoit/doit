import os
from six import StringIO

import pytest
from mock import Mock

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit import reporter, runner
from doit.cmd_run import Run
from doit.dependency import MD5Checker
from tests.conftest import tasks_sample


class TestCmdRun(object):

    def testProcessRun(self, dependency1, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        result = cmd_run._execute(output)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunMP(self, dependency1, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        result = cmd_run._execute(output, num_process=1)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunMThread(self, dependency1, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        result = cmd_run._execute(output, num_process=1, par_type='thread')
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testInvalidParType(self, dependency1, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_run._execute,
                      output, num_process=1, par_type='not_exist')


    def testMP_not_available(self, dependency1, depfile_name,
                             capsys, monkeypatch):
        # make sure MRunner wont be used
        monkeypatch.setattr(runner.MRunner, "available",
                            Mock(return_value=False))
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        result = cmd_run._execute(output, num_process=1)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got
        err = capsys.readouterr()[1]
        assert "WARNING:" in err
        assert "parallel using threads" in err

    def testProcessRunFilter(self, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample(), sel_tasks=["g1.a"])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got

    def testProcessRunSingle(self, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample(), sel_tasks=["t3"])
        cmd_run._execute(output, single=True)
        got = output.getvalue().split("\n")[:-1]
        # t1 is a depenendency of t3 but not included
        assert [".  t3"] == got

    def testProcessRunSingleSubtasks(self, depfile_name):
        output = StringIO()
        task_list = tasks_sample()
        assert task_list[4].name == 'g1.b'
        task_list[4].task_dep = ['t3']
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=task_list, sel_tasks=["g1"])
        cmd_run._execute(output, single=True)
        got = output.getvalue().split("\n")[:-1]
        # t3 is a depenendency of g1.b but not included
        assert [".  g1.a", ".  g1.b"] == got

    def testProcessRunEmptyFilter(self, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample(), sel_tasks=[])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        assert [] == got

    def testInvalidReporter(self, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_run._execute,
                      output, reporter="i dont exist")

    def testReporterInstance(self, depfile_name):
        output = StringIO()
        class MyReporter(reporter.ConsoleReporter):
            def get_status(self, task):
                self.outstream.write('MyReporter.start %s\n' % task.name)
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=[tasks_sample()[0]])
        cmd_run._execute(output, reporter=MyReporter(output, {}))
        got = output.getvalue().split("\n")[:-1]
        assert 'MyReporter.start t1' == got[0]

    def testCustomReporter(self, depfile_name):
        output = StringIO()
        class MyReporter(reporter.ConsoleReporter):
            def get_status(self, task):
                self.outstream.write('MyReporter.start %s\n' % task.name)
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=[tasks_sample()[0]])
        cmd_run._execute(output, reporter=MyReporter)
        got = output.getvalue().split("\n")[:-1]
        assert 'MyReporter.start t1' == got[0]

    def testInvalidChecker(self, depfile_name):
        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_run._execute,
                      output, check_file_uptodate="i dont exist")

    def testCustomChecker(self, depfile_name):
        class MyChecker(MD5Checker):
            pass

        output = StringIO()
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=[tasks_sample()[0]])
        result = cmd_run._execute(output, check_file_uptodate=MyChecker)
        assert 0 == result

    def testSetVerbosity(self, depfile_name):
        output = StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        cmd_run = Run(backend='dbm', dep_file=depfile_name, task_list=[t])
        cmd_run._execute(output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity

    def test_outfile(self, depfile_name):
        cmd_run = Run(backend='dbm', dep_file=depfile_name,
                      task_list=tasks_sample(), sel_tasks=["g1.a"])
        cmd_run._execute('test.out')
        try:
            outfile = open('test.out', 'r')
            got = outfile.read()
            outfile.close()
            assert ".  g1.a\n" == got
        finally:
            if os.path.exists('test.out'):
                os.remove('test.out')
