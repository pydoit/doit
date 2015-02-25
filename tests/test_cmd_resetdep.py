import pytest
from six import StringIO

from doit.cmd_resetdep import ResetDep
from doit.dependency import TimestampChecker
from doit.exceptions import InvalidCommand
from doit.task import Task
from tests.conftest import tasks_sample, CmdFactory


class TestCmdResetDep(object):

    def test_execute(self, depfile, dependency1):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                              dep_manager=depfile)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ["processed %s" % t.name for t in tasks]
        assert sorted(expected) == sorted(got)

    def test_file_dep(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        output = StringIO()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                              dep_manager=depfile)
        cmd_list._execute()
        got = output.getvalue()
        assert "processed t2\n" == got

    def test_file_dep_up_to_date(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        depfile.save_success(my_task)
        output = StringIO()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                              dep_manager=depfile)
        cmd_list._execute()
        got = output.getvalue()
        assert "skip t2\n" == got

    def test_file_dep_change_checker(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        depfile.save_success(my_task)
        depfile.checker = TimestampChecker()
        output = StringIO()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                              dep_manager=depfile)
        cmd_list._execute()
        got = output.getvalue()
        assert "processed t2\n" == got

    def test_filter(self, depfile, dependency1):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                              dep_manager=depfile)
        cmd_list._execute(pos_args=['t2'])
        got = output.getvalue()
        assert "processed t2\n" == got

    def test_invalid_task(self, depfile):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                              dep_manager=depfile)
        pytest.raises(InvalidCommand, cmd_list._execute, pos_args=['xxx'])
