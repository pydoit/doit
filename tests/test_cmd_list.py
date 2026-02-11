import unittest
from io import StringIO

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.tools import result_dep
from doit.cmd_list import List
from tests.support import tasks_sample, tasks_bad_sample, CmdFactory
from tests.support import DepManagerMixin, DependencyFileMixin


class TestCmdList(unittest.TestCase):

    def testQuiet(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in tasks if not t.subtask_of]
        self.assertEqual(sorted(expected), got)

    def testDoc(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(quiet=False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        for t in sorted(tasks):
            if not t.subtask_of:
                expected.append([t.name, t.doc])
        self.assertEqual(len(expected), len(got))
        for exp1, got1 in zip(expected, got):
            self.assertEqual(exp1, got1.split(None, 1))

    def testCustomTemplate(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(template='xxx {name} xxx {doc}')
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual('xxx g1 xxx g1 doc string', got[0])
        self.assertEqual('xxx t3 xxx t3 doc string', got[3])

    def testDependencies(self):
        my_task = Task("t2", [""], file_dep=['d2.txt'])
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=[my_task])
        cmd_list._execute(list_deps=True)
        got = output.getvalue()
        self.assertIn("d2.txt", got)

    def testSubTask(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in sorted(tasks)]
        self.assertEqual(expected, got)

    def testFilter(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1', 't2'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['g1', 't2'], got)

    def testFilterSubtask(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1.a'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['g1.a'], got)

    def testFilterAll(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(subtasks=True, pos_args=['g1'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['g1', 'g1.a', 'g1.b'], got)

    def testNoPrivate(self):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute(pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual([], got)

    def testWithPrivate(self):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute(private=True, pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['_s3'], got)

    def testListInvalidTask(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        self.assertRaises(InvalidCommand, cmd_list._execute, pos_args=['xxx'])

    def testSortByName(self):
        task_list = list(tasks_sample())
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['g1', 't1', 't2', 't3'], got)

    def testSortByDefinition(self):
        task_list = list(tasks_sample())
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute(sort='definition')
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual(['t1', 't2', 'g1', 't3'], got)


class TestCmdListWithDeps(DependencyFileMixin, DepManagerMixin, unittest.TestCase):

    def testStatus(self):
        task_list = tasks_sample()
        self.dep_manager.ignore(task_list[0])  # t1
        self.dep_manager.save_success(task_list[1])  # t2
        self.dep_manager.close()

        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=self.dep_manager.name,
                              backend='dbm', task_list=task_list)
        cmd_list._execute(status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertIn('R g1', got)
        self.assertIn('I t1', got)
        self.assertIn('U t2', got)

    def testErrorStatus(self):
        """Check that problematic tasks show an 'E' as status."""
        task_list = tasks_bad_sample()
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_manager=self.dep_manager,
                              task_list=task_list)
        cmd_list._execute(status=True)
        for line in output.getvalue().split('\n'):
            if line:
                self.assertTrue(line.strip().startswith('E '))

    def testStatus_result_dep_bug_gh44(self):
        task_list = [Task("t1", [""], doc="t1 doc string"),
                     Task("t2", [""], uptodate=[result_dep('t1')])]
        self.dep_manager.save_success(task_list[0])  # t1
        self.dep_manager.close()

        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=self.dep_manager.name,
                              backend='dbm', task_list=task_list)
        cmd_list._execute(status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertIn('R t1', got)
        self.assertIn('R t2', got)

    def test_unicode_name(self):
        task_list = [Task("t做", [""], doc="t1 doc string 做")]
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=self.dep_manager.name,
                              task_list=task_list)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        self.assertEqual('t做', got[0])
