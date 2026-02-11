import unittest
from io import StringIO

from doit.exceptions import InvalidCommand
from doit.dependency import DbmDB, Dependency
from doit.cmd_ignore import Ignore
from tests.support import tasks_sample, CmdFactory, DepManagerMixin


class TestCmdIgnore(DepManagerMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.tasks = tasks_sample()

    def testIgnoreAll(self):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=self.dep_manager,
                         task_list=self.tasks)
        cmd._execute([])
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(["You cant ignore all tasks! Please select a task."], got)
        for task in self.tasks:
            self.assertIsNone(self.dep_manager._get(task.name, "ignore:"))

    def testIgnoreOne(self):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=self.dep_manager,
                         task_list=self.tasks)
        cmd._execute(["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        self.assertEqual(["ignoring t2", "ignoring t1"], got)
        dep = Dependency(DbmDB, self.dep_manager.name)
        self.assertEqual('1', dep._get("t1", "ignore:"))
        self.assertEqual('1', dep._get("t2", "ignore:"))
        self.assertIsNone(dep._get("t3", "ignore:"))

    def testIgnoreGroup(self):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=self.dep_manager,
                         task_list=self.tasks)
        cmd._execute(["g1"])

        dep = Dependency(DbmDB, self.dep_manager.name)
        self.assertIsNone(dep._get("t1", "ignore:"))
        self.assertIsNone(dep._get("t2", "ignore:"))
        self.assertEqual('1', dep._get("g1", "ignore:"))
        self.assertEqual('1', dep._get("g1.a", "ignore:"))
        self.assertEqual('1', dep._get("g1.b", "ignore:"))

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=self.dep_manager,
                         task_list=self.tasks)
        cmd._execute(["t3"])
        dep = Dependency(DbmDB, self.dep_manager.name)
        self.assertEqual('1', dep._get("t3", "ignore:"))
        self.assertIsNone(dep._get("t1", "ignore:"))

    def testIgnoreInvalid(self):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=self.dep_manager,
                         task_list=self.tasks)
        self.assertRaises(InvalidCommand, cmd._execute, ["XXX"])
