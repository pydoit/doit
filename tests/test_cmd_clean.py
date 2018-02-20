from io import StringIO
from unittest import mock

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_clean import Clean
from .conftest import CmdFactory

class TestCmdClean(object):

    @pytest.fixture
    def tasks(self, request):
        self.cleaned = []
        def myclean(name):
            self.cleaned.append(name)
        return [
            Task("t1", None, targets=['t1.out'], setup=['t2'],
                 clean=[(myclean,('t1',))]),
            Task("t2", None, clean=[(myclean,('t2',))]),
            Task("t3", None, task_dep=['t3:a'], has_subtask=True,
                 clean=[(myclean,('t3',))]),
            Task("t3:a", None, clean=[(myclean,('t3:a',))], subtask_of='t3'),
            Task("t4", None, file_dep=['t1.out'], clean=[(myclean,('t4',))] ),
            ]

    def test_clean_all(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=True,
                           cleanforget=False)
        # all enables --clean-dep
        assert ['t4', 't1', 't2', 't3', 't3:a'] == self.cleaned

    def test_clean_default_all(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False)
        # default enables --clean-dep
        assert ['t4', 't1', 't2', 't3', 't3:a'] == self.cleaned

    def test_clean_default(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=tasks,
            sel_tasks=['t1'], dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False)
        # default enables --clean-dep
        assert ['t1', 't2'] == self.cleaned

    def test_clean_selected(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=tasks,
            sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False, pos_args=['t2'])
        assert ['t2'] == self.cleaned
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t1'])
        assert ['t1', 't2'] == self.cleaned
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep_recursive(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t4'])
        assert ['t4', 't1', 't2'] == self.cleaned

    def test_clean_subtasks(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False, pos_args=['t3'])
        assert ['t3', 't3:a'] == self.cleaned

    def test_clean_taskdep_once(self, tasks):
        # do not execute clean operation more than once
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t1', 't2'])
        assert ['t1', 't2'] == self.cleaned

    def test_clean_invalid_task(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               sel_tasks=['t1'])
        pytest.raises(InvalidCommand, cmd_clean._execute,
                      dryrun=False, cleandep=False, cleanall=False,
                      cleanforget=False, pos_args=['xxxx'])

    def test_clean_forget_selected(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=tasks,
            sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=True, pos_args=['t2'])
        assert ['t2'] == self.cleaned
        # order
        mock_dep_manager.assert_has_calls(
            [mock.call.remove(mock.ANY), mock.call.close()])
        # exactly t2, not more
        assert (mock_dep_manager.remove.call_args_list ==
                [mock.call('t2')])

    def test_clean_forget_taskdep(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=True, pos_args=['t1'])
        assert ['t1', 't2'] == self.cleaned
        # order
        mock_dep_manager.assert_has_calls(
            [mock.call.remove(mock.ANY), mock.call.close()])
        assert (mock_dep_manager.remove.call_args_list ==
                [mock.call('t1'), mock.call('t2')])
