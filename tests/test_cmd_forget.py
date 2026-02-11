import unittest
from io import StringIO

from doit.exceptions import InvalidCommand
from doit.dependency import DbmDB, Dependency
from doit.cmd_forget import Forget
from tests.support import tasks_sample, CmdFactory, DepfileNameMixin


class TestCmdForget(DepfileNameMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.tasks = tasks_sample()

    @staticmethod
    def _add_task_deps(tasks, testdb):
        """put some data on testdb"""
        dep = Dependency(DbmDB, testdb)
        for task in tasks:
            dep._set(task.name, "dep", "1")
        dep.close()

        dep2 = Dependency(DbmDB, testdb)
        assert "1" == dep2._get("g1.a", "dep")
        dep2.close()

    def testForgetDefault(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(Forget, outstream=output, dep_file=self.depfile_name,
                                backend='dbm', task_list=self.tasks,
                                sel_tasks=['t1', 't2'])
        cmd_forget._execute(False, False, False)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(["forgetting t1", "forgetting t2"], got)
        dep = Dependency(DbmDB, self.depfile_name)
        self.assertIsNone(dep._get('t1', "dep"))
        self.assertIsNone(dep._get('t2', "dep"))
        self.assertEqual('1', dep._get('t3', "dep"))

    def testForgetAll(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(Forget, outstream=output, dep_file=self.depfile_name,
                                backend='dbm', task_list=self.tasks, sel_tasks=[])
        cmd_forget._execute(False, False, True)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(["forgetting all tasks"], got)
        dep = Dependency(DbmDB, self.depfile_name)
        for task in self.tasks:
            self.assertIsNone(dep._get(task.name, "dep"))

    def testDisableDefault(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(Forget, outstream=output, dep_file=self.depfile_name,
                                backend='dbm', task_list=self.tasks,
                                sel_tasks=['t1', 't2'], sel_default_tasks=True)
        cmd_forget._execute(False, True, False)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(
            ["no tasks specified, pass task name, --enable-default or --all"], got)
        dep = Dependency(DbmDB, self.depfile_name)
        for task in self.tasks:
            self.assertEqual("1", dep._get(task.name, "dep"))

    def testForgetOne(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(Forget, outstream=output, dep_file=self.depfile_name,
                                backend='dbm', task_list=self.tasks,
                                sel_tasks=["t2", "t1"])
        cmd_forget._execute(False, True, False)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(["forgetting t2", "forgetting t1"], got)
        dep = Dependency(DbmDB, self.depfile_name)
        self.assertIsNone(dep._get("t1", "dep"))
        self.assertIsNone(dep._get("t2", "dep"))
        self.assertEqual("1", dep._get("g1.a", "dep"))

    def testForgetGroup(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(
            Forget, outstream=output, dep_file=self.depfile_name,
            backend='dbm', task_list=self.tasks, sel_tasks=["g1"])
        cmd_forget._execute(False, False, False)
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual("forgetting g1", got[0])

        dep = Dependency(DbmDB, self.depfile_name)
        self.assertEqual("1", dep._get("t1", "dep"))
        self.assertEqual("1", dep._get("t2", "dep"))
        self.assertIsNone(dep._get("g1", "dep"))
        self.assertIsNone(dep._get("g1.a", "dep"))
        self.assertIsNone(dep._get("g1.b", "dep"))

    def testForgetTaskDependency(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(
            Forget, outstream=output, dep_file=self.depfile_name,
            backend='dbm', task_list=self.tasks, sel_tasks=["t3"])
        cmd_forget._execute(True, False, False)
        dep = Dependency(DbmDB, self.depfile_name)
        self.assertIsNone(dep._get("t3", "dep"))
        self.assertIsNone(dep._get("t1", "dep"))

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(
            Forget, outstream=output, dep_file=self.depfile_name,
            backend='dbm', task_list=self.tasks, sel_tasks=["t3"])
        cmd_forget._execute(False, False, False)
        dep = Dependency(DbmDB, self.depfile_name)
        self.assertIsNone(dep._get("t3", "dep"))
        self.assertEqual("1", dep._get("t1", "dep"))

    def testForgetInvalid(self):
        self._add_task_deps(self.tasks, self.depfile_name)
        output = StringIO()
        cmd_forget = CmdFactory(
            Forget, outstream=output, dep_file=self.depfile_name,
            backend='dbm', task_list=self.tasks, sel_tasks=["XXX"])
        self.assertRaises(InvalidCommand, cmd_forget._execute, False, False, False)
