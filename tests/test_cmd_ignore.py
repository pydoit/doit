from io import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import DbmDB, Dependency
from doit.cmd_ignore import Ignore
from .conftest import tasks_sample, CmdFactory


class TestCmdIgnore(object):

    @pytest.fixture
    def tasks(self, request):
        return tasks_sample()

    def testIgnoreAll(self, tasks, dep_manager):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=dep_manager,
                         task_list=tasks)
        cmd._execute([])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        for task in tasks:
            assert None == dep_manager._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks, dep_manager):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=dep_manager,
                         task_list=tasks)
        cmd._execute(["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(DbmDB, dep_manager.name)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks, dep_manager):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=dep_manager,
                         task_list=tasks)
        cmd._execute(["g1"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(DbmDB, dep_manager.name)
        assert None == dep._get("t1", "ignore:"), got
        assert None == dep._get("t2", "ignore:")
        assert '1' == dep._get("g1", "ignore:")
        assert '1' == dep._get("g1.a", "ignore:")
        assert '1' == dep._get("g1.b", "ignore:")

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self, tasks, dep_manager):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=dep_manager,
                         task_list=tasks)
        cmd._execute(["t3"])
        dep = Dependency(DbmDB, dep_manager.name)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks, dep_manager):
        output = StringIO()
        cmd = CmdFactory(Ignore, outstream=output, dep_manager=dep_manager,
                         task_list=tasks)
        pytest.raises(InvalidCommand, cmd._execute, ["XXX"])
