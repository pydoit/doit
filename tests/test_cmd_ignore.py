import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import Dependency
from doit.task import Task
from doit.cmd_ignore import Ignore
doit_ignore = Ignore._execute


class TestCmdIgnore(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            # FIXME DRY
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



    def testIgnoreAll(self, tasks, depfile):
        output = StringIO.StringIO()
        doit_ignore(depfile.name, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks, depfile):
        output = StringIO.StringIO()
        doit_ignore(depfile.name, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(depfile.name)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks, depfile):
        output = StringIO.StringIO()
        doit_ignore(depfile.name, tasks, output, ["g2"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(depfile.name)
        assert '1' == dep._get("t1", "ignore:"), got
        assert None == dep._get("t2", "ignore:")
        assert '1' == dep._get("g1", "ignore:")
        assert '1' == dep._get("g1.a", "ignore:")
        assert '1' == dep._get("g1.b", "ignore:")
        assert '1' == dep._get("g2", "ignore:")

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self, tasks, depfile):
        output = StringIO.StringIO()
        doit_ignore(depfile.name, tasks, output, ["t3"])
        dep = Dependency(depfile.name)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks, depfile):
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, doit_ignore,
                       depfile.name, tasks, output, ["XXX"])



