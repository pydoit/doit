import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import Dependency
from doit.task import Task
from doit.cmd_forget import doit_forget


class TestCmdForget(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            tasks = [Task("t1", [""]),
                     Task("t2", [""]),
                     Task("g1", None, task_dep=['g1.a','g1.b']),
                     Task("g1.a", [""]),
                     Task("g1.b", [""]),
                     Task("t3", [""], task_dep=['t1']),
                     Task("g2", None, task_dep=['t1','g1'])]
            return tasks
        return request.cached_setup(
            setup=create_tasks,
            scope="function")

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
        output = StringIO.StringIO()
        doit_forget(depfile.name, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        doit_forget(depfile.name, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(depfile.name)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")
        assert "1" == dep._get("g1.a", "dep")

    def testForgetGroup(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        doit_forget(depfile.name, tasks, output, ["g2"])
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
        output = StringIO.StringIO()
        doit_forget(depfile.name, tasks, output, ["t3"])
        dep = Dependency(depfile.name)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, doit_forget,
                       depfile.name, tasks, output, ["XXX"])


