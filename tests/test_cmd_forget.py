from six import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import Dependency
from doit.cmd_forget import Forget
from .conftest import tasks_sample


class TestCmdForget(object):

    @pytest.fixture
    def tasks(self, request):
        return tasks_sample()

    @staticmethod
    def _add_task_deps(tasks, testdb):
        """put some data on testdb"""
        dep = Dependency(testdb)
        for task in tasks:
            dep._set(task.name,"dep","1")
        dep.close()

        dep2 = Dependency(testdb)
        assert "1" == dep2._get("g1.a", "dep")
        dep2.close()


    def testForgetAll(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks, sel_tasks=[])
        cmd_forget._execute(False)
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks,
                            sel_tasks=["t2", "t1"])
        cmd_forget._execute(False)
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(depfile.name)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")
        assert "1" == dep._get("g1.a", "dep")

    def testForgetGroup(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks, sel_tasks=["g1"])
        cmd_forget._execute(False)
        got = output.getvalue().split("\n")[:-1]
        assert "forgeting g1" == got[0]

        dep = Dependency(depfile.name)
        assert "1" == dep._get("t1", "dep")
        assert "1" == dep._get("t2", "dep")
        assert None == dep._get("g1", "dep")
        assert None == dep._get("g1.a", "dep")
        assert None == dep._get("g1.b", "dep")


    def testForgetTaskDependency(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks, sel_tasks=["t3"])
        cmd_forget._execute(True)
        dep = Dependency(depfile.name)
        assert None == dep._get("t3", "dep")
        assert None == dep._get("t1", "dep")

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks, sel_tasks=["t3"])
        cmd_forget._execute(False)
        dep = Dependency(depfile.name)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            backend='dbm', task_list=tasks, sel_tasks=["XXX"])
        pytest.raises(InvalidCommand, cmd_forget._execute, False)
