import unittest
from io import StringIO

from doit.cmd_resetdep import ResetDep
from doit.dependency import TimestampChecker, get_md5, get_file_md5
from doit.exceptions import InvalidCommand
from doit.task import Task
from tests.support import tasks_sample, CmdFactory, get_abspath
from tests.support import DepManagerMixin, DependencyFileMixin


class TestCmdResetDep(DependencyFileMixin, DepManagerMixin, unittest.TestCase):

    def test_execute(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ["processed %s" % t.name for t in tasks]
        self.assertEqual(sorted(expected), sorted(got))

    def test_file_dep(self):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        self.assertEqual("processed t2\n", output.getvalue())

        dep = list(my_task.file_dep)[0]
        timestamp, size, md5 = self.dep_manager._get(my_task.name, dep)
        self.assertEqual(get_file_md5(get_abspath("data/dependency1")), md5)

    def test_file_dep_up_to_date(self):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        self.dep_manager.save_success(my_task)
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        self.assertEqual("skip t2\n", output.getvalue())

    def test_file_dep_change_checker(self):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        self.dep_manager.save_success(my_task)
        self.dep_manager.checker = TimestampChecker()
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        self.assertEqual("processed t2\n", output.getvalue())

    def test_filter(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=self.dep_manager)
        cmd_reset._execute(pos_args=['t2'])
        self.assertEqual("processed t2\n", output.getvalue())

    def test_invalid_task(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=self.dep_manager)
        self.assertRaises(InvalidCommand, cmd_reset._execute, pos_args=['xxx'])

    def test_missing_file_dep(self):
        my_task = Task("t2", [""], file_dep=['tests/data/missing'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        self.assertEqual(
            "failed t2 (Dependent file 'tests/data/missing' does not exist.)\n",
            output.getvalue())

    def test_missing_dep_and_target(self):
        task_a = Task("task_a", [""],
                      file_dep=['tests/data/dependency1'],
                      targets=['tests/data/dependency2'])
        task_b = Task("task_b", [""],
                      file_dep=['tests/data/dependency2'],
                      targets=['tests/data/dependency3'])
        task_c = Task("task_c", [""],
                      file_dep=['tests/data/dependency3'],
                      targets=['tests/data/dependency4'])

        output = StringIO()
        tasks = [task_a, task_b, task_c]
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=self.dep_manager)
        cmd_reset._execute()

        self.assertEqual(
            "processed task_a\n"
            "processed task_b\n"
            "failed task_c (Dependent file 'tests/data/dependency3'"
            " does not exist.)\n",
            output.getvalue())

    def test_values_and_results(self):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        my_task.result = "result"
        my_task.values = {'x': 5, 'y': 10}
        self.dep_manager.save_success(my_task)
        self.dep_manager.checker = TimestampChecker()  # trigger task update

        reseted = Task("t2", [""], file_dep=['tests/data/dependency1'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[reseted],
                               dep_manager=self.dep_manager)
        cmd_reset._execute()
        self.assertEqual("processed t2\n", output.getvalue())
        self.assertEqual({'x': 5, 'y': 10},
                         self.dep_manager.get_values(reseted.name))
        self.assertEqual(get_md5('result'),
                         self.dep_manager.get_result(reseted.name))
