from io import StringIO

import pytest

from doit.cmd_resetdep import ResetDep
from doit.dependency import TimestampChecker, get_md5, get_file_md5
from doit.exceptions import InvalidCommand
from doit.task import Task
from tests.conftest import tasks_sample, CmdFactory, get_abspath


class TestCmdResetDep(object):

    def test_execute(self, depfile, dependency1):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=depfile)
        cmd_reset._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ["processed %s" % t.name for t in tasks]
        assert sorted(expected) == sorted(got)

    def test_file_dep(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=depfile)
        cmd_reset._execute()
        got = output.getvalue()
        assert "processed t2\n" == got

        dep = list(my_task.file_dep)[0]
        timestamp, size, md5 = depfile._get(my_task.name, dep)
        assert get_file_md5(get_abspath("data/dependency1")) == md5

    def test_file_dep_up_to_date(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        depfile.save_success(my_task)
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=depfile)
        cmd_reset._execute()
        got = output.getvalue()
        assert "skip t2\n" == got

    def test_file_dep_change_checker(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        depfile.save_success(my_task)
        depfile.checker = TimestampChecker()
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=depfile)
        cmd_reset._execute()
        got = output.getvalue()
        assert "processed t2\n" == got

    def test_filter(self, depfile, dependency1):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=depfile)
        cmd_reset._execute(pos_args=['t2'])
        got = output.getvalue()
        assert "processed t2\n" == got

    def test_invalid_task(self, depfile):
        output = StringIO()
        tasks = tasks_sample()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=tasks,
                               dep_manager=depfile)
        pytest.raises(InvalidCommand, cmd_reset._execute, pos_args=['xxx'])

    def test_missing_file_dep(self, depfile):
        my_task = Task("t2", [""], file_dep=['tests/data/missing'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[my_task],
                               dep_manager=depfile)
        cmd_reset._execute()
        got = output.getvalue()
        assert ("failed t2 (Dependent file 'tests/data/missing' does not "
                "exist.)\n") == got

    def test_missing_dep_and_target(self, depfile, dependency1, dependency2):

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
                               dep_manager=depfile)
        cmd_reset._execute()

        got = output.getvalue()
        assert ("processed task_a\n"
                "processed task_b\n"
                "failed task_c (Dependent file 'tests/data/dependency3'"
                " does not exist.)\n") == got

    def test_values_and_results(self, depfile, dependency1):
        my_task = Task("t2", [""], file_dep=['tests/data/dependency1'])
        my_task.result = "result"
        my_task.values = {'x': 5, 'y': 10}
        depfile.save_success(my_task)
        depfile.checker = TimestampChecker()  # trigger task update

        reseted = Task("t2", [""], file_dep=['tests/data/dependency1'])
        output = StringIO()
        cmd_reset = CmdFactory(ResetDep, outstream=output, task_list=[reseted],
                               dep_manager=depfile)
        cmd_reset._execute()
        got = output.getvalue()
        assert "processed t2\n" == got
        assert {'x': 5, 'y': 10} == depfile.get_values(reseted.name)
        assert get_md5('result') == depfile.get_result(reseted.name)
