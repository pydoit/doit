from io import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_info import Info
from .conftest import CmdFactory


class TestCmdInfo(object):

    def test_info_basic_attrs(self, dep_manager):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'],
                    doc="task doc", getargs={'a': ('x', 'y')}, verbosity=2)
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=dep_manager.name, task_list=[task])
        cmd._execute(['t1'], hide_status=True)
        assert "t1" in output.getvalue()
        assert "task doc" in output.getvalue()
        assert "- tests/data/dependency1" in output.getvalue()
        assert "verbosity  : 2" in output.getvalue()
        assert "getargs    : {'a': ('x', 'y')}" in output.getvalue()

    def test_invalid_command_args(self, dep_manager):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=dep_manager.name, task_list=[task])
        # fails if number of args != 1
        pytest.raises(InvalidCommand, cmd._execute, [])
        pytest.raises(InvalidCommand, cmd._execute, ['t1', 't2'])

    def test_execute_status_run(self, dep_manager, dependency1):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=dep_manager.name, task_list=[task],
                         dep_manager=dep_manager)
        return_val = cmd._execute(['t1'])
        assert "t1" in output.getvalue()
        assert return_val == 1  # indicates task is not up-to-date
        assert "status" in output.getvalue()
        assert ": run" in output.getvalue()
        assert " - tests/data/dependency1" in output.getvalue()

    def test_hide_execute_status(self, dep_manager, dependency1):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_manager=dep_manager, task_list=[task])
        return_val = cmd._execute(['t1'], hide_status=True)
        assert "t1" in output.getvalue()
        assert return_val == 0  # always zero if not showing status
        assert "status" not in output.getvalue()
        assert ": run" not in output.getvalue()

    def test_execute_status_uptodate(self, dep_manager, dependency1):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_manager=dep_manager, task_list=[task])
        cmd.dep_manager.save_success(task)
        return_val = cmd._execute(['t1'])
        assert "t1" in output.getvalue()
        assert return_val == 0  # indicates task is not up-to-date
        assert ": up-to-date" in output.getvalue()


    def test_get_reasons_str(self):
        reasons = {
            'has_no_dependencies': True,
            'uptodate_false': [('func', 'arg', 'kwarg')],
            'checker_changed': ['foo', 'bar'],
            'missing_target': ['f1', 'f2'],
        }

        got = Info.get_reasons(reasons).splitlines()
        assert len(got) == 7
        assert got[0] == ' * The task has no dependencies.'
        assert got[1] == ' * The following uptodate objects evaluate to false:'
        assert got[2] == '    - func (args=arg, kwargs=kwarg)'
        assert got[3] == ' * The file_dep checker changed from foo to bar.'
        assert got[4] == ' * The following targets do not exist:'
        assert got[5] == '    - f1'
        assert got[6] == '    - f2'
