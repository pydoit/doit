import os
import io
import contextlib
import unittest
from io import StringIO
from unittest.mock import Mock, patch

from doit.exceptions import InvalidCommand
from doit import reporter, runner
from doit.cmd_run import Run
from tests.support import tasks_sample, CmdFactory
from tests.support import DepfileNameMixin, DependencyFileMixin


class TestCmdRun(DependencyFileMixin, DepfileNameMixin, unittest.TestCase):

    def testProcessRun(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(self.dependency1))
        result = cmd_run._execute(output)
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"], got)

    @unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
    def testProcessRunMP(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(self.dependency1))
        result = cmd_run._execute(output, num_process=1)
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"], got)

    def testProcessRunMThread(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(self.dependency1))
        result = cmd_run._execute(output, num_process=1, par_type='thread')
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"], got)

    def testInvalidParType(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample())
        self.assertRaises(InvalidCommand, cmd_run._execute,
                          output, num_process=1, par_type='not_exist')

    def testMP_not_available(self):
        err = io.StringIO()
        with patch.object(runner.MRunner, "available",
                          Mock(return_value=False)):
            with contextlib.redirect_stderr(err):
                output = StringIO()
                cmd_run = CmdFactory(
                    Run, backend='dbm', dep_file=self.depfile_name,
                    task_list=tasks_sample(self.dependency1))
                result = cmd_run._execute(output, num_process=1)
                self.assertEqual(0, result)
                got = output.getvalue().split("\n")[:-1]
                self.assertEqual(
                    [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"], got)
        err_output = err.getvalue()
        self.assertIn("WARNING:", err_output)
        self.assertIn("parallel using threads", err_output)

    def testProcessRunFilter(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(), sel_tasks=["g1.a"])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([".  g1.a"], got)

    def testProcessRunSingle(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(), sel_tasks=["t3"])
        cmd_run._execute(output, single=True)
        got = output.getvalue().split("\n")[:-1]
        # t1 is a dependency of t3 but not included
        self.assertEqual([".  t3"], got)

    def testProcessRunSingleSubtasks(self):
        output = StringIO()
        task_list = tasks_sample()
        self.assertEqual(task_list[4].name, 'g1.b')
        task_list[4].task_dep = ['t3']
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=task_list, sel_tasks=["g1"])
        cmd_run._execute(output, single=True)
        got = output.getvalue().split("\n")[:-1]
        # t3 is a dependency of g1.b but not included
        self.assertEqual([".  g1.a", ".  g1.b"], got)

    def testProcessRunSingleWithArgs(self):
        output = StringIO()
        task_list = tasks_sample()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=task_list,
                             sel_tasks=["t1", "--arg1", "ABC"])
        cmd_run._execute(output, single=True)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([".  t1"], got)

    def testProcessRunEmptyFilter(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(), sel_tasks=[])
        cmd_run._execute(output)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual([], got)


class MyReporter(reporter.ConsoleReporter):
    def get_status(self, task):
        self.outstream.write('MyReporter.start %s\n' % task.name)


class TestCmdRunReporter(DepfileNameMixin, unittest.TestCase):

    def testReporterInstance(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=[tasks_sample()[0]])
        cmd_run._execute(output, reporter=MyReporter(output, {}))
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual('MyReporter.start t1', got[0])

    def testCustomReporter(self):
        output = StringIO()
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=[tasks_sample()[0]])
        cmd_run._execute(output, reporter=MyReporter)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual('MyReporter.start t1', got[0])

    def testPluginReporter(self):
        output = StringIO()
        cmd_run = CmdFactory(
            Run, backend='dbm',
            dep_file=self.depfile_name,
            task_list=[tasks_sample()[0]],
            config={'REPORTER': {'my': 'tests.test_cmd_run:MyReporter'}})
        cmd_run._execute(output, reporter='my')
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual('MyReporter.start t1', got[0])


class TestCmdRunOptions(DepfileNameMixin, unittest.TestCase):

    def test_outfile(self):
        cmd_run = CmdFactory(Run, backend='dbm', dep_file=self.depfile_name,
                             task_list=tasks_sample(), sel_tasks=["g1.a"])
        cmd_run._execute('test.out')
        try:
            outfile = open('test.out', 'r')
            got = outfile.read()
            outfile.close()
            self.assertEqual(".  g1.a\n", got)
        finally:
            if os.path.exists('test.out'):
                os.remove('test.out')
