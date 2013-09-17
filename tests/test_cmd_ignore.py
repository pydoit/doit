from six import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.dependency import Dependency
from doit.cmd_ignore import Ignore
from .conftest import tasks_sample


class TestCmdIgnore(object):

    @pytest.fixture
    def tasks(self, request):
        return tasks_sample()

    def testIgnoreAll(self, tasks, depfile_name):
        output = StringIO()
        cmd = Ignore(outstream=output, dep_file=depfile_name,
                     backend='dbm', task_list=tasks)
        cmd._execute([])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        dep = Dependency(depfile_name)
        for task in tasks:
            assert None == dep._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks, depfile_name):
        output = StringIO()
        cmd = Ignore(outstream=output, dep_file=depfile_name,
                     backend='dbm', task_list=tasks)
        cmd._execute(["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(depfile_name)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks, depfile_name):
        output = StringIO()
        cmd = Ignore(outstream=output, dep_file=depfile_name,
                     backend='dbm', task_list=tasks)
        cmd._execute(["g1"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(depfile_name)
        assert None == dep._get("t1", "ignore:"), got
        assert None == dep._get("t2", "ignore:")
        assert '1' == dep._get("g1", "ignore:")
        assert '1' == dep._get("g1.a", "ignore:")
        assert '1' == dep._get("g1.b", "ignore:")

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self, tasks, depfile_name):
        output = StringIO()
        cmd = Ignore(outstream=output, dep_file=depfile_name,
                     backend='dbm', task_list=tasks)
        cmd._execute(["t3"])
        dep = Dependency(depfile_name)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks, depfile_name):
        output = StringIO()
        cmd = Ignore(outstream=output, dep_file=depfile_name,
                     backend='dbm', task_list=tasks)
        pytest.raises(InvalidCommand, cmd._execute, ["XXX"])
