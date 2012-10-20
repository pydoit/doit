from StringIO import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import Dependency
from doit.task import Task
from doit.cmd_forget import Forget


class TestCmdForget(object):

    @pytest.fixture
    def tasks(self, request):
        return [Task("t1", [""]),
                Task("t2", [""]),
                Task("g1", None, task_dep=['g1.a','g1.b']),
                Task("g1.a", [""]),
                Task("g1.b", [""]),
                Task("t3", [""], task_dep=['t1']),
                Task("g2", None, task_dep=['t1','g1'])]


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
                            task_list=tasks, sel_tasks=[])
        cmd_forget._execute()
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            task_list=tasks, sel_tasks=["t2", "t1"])
        cmd_forget._execute()
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
                            task_list=tasks, sel_tasks=["g2"])
        cmd_forget._execute()
        got = output.getvalue().split("\n")[:-1]
        assert "forgeting g2" == got[0]

        dep = Dependency(depfile.name)
        assert None == dep._get("t1", "dep")
        assert "1" == dep._get("t2", "dep")
        assert None == dep._get("g1", "dep")
        assert None == dep._get("g1.a", "dep")
        assert None == dep._get("g1.b", "dep")
        assert None == dep._get("g2", "dep")

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            task_list=tasks, sel_tasks=["t3"])
        cmd_forget._execute()
        dep = Dependency(depfile.name)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO()
        cmd_forget = Forget(outstream=output, dep_file=depfile.name,
                            task_list=tasks, sel_tasks=["XXX"])
        pytest.raises(InvalidCommand, cmd_forget._execute)


