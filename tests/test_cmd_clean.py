from io import StringIO
import mock
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
            Task("t1", None, task_dep=['t2'], clean=[(myclean,('t1',))]),
            Task("t2", None, clean=[(myclean,('t2',))]),
            Task("t3", None, task_dep=['t3:a'], has_subtask=True,
                 clean=[(myclean,('t3',))]),
            Task("t3:a", None, clean=[(myclean,('t3:a',))], is_subtask=True),
            Task("t4", None, task_dep=['t1'], clean=[(myclean,('t4',))] ),
            ]

    def test_clean_all(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(False, False, True, False)
        assert ['t1','t2', 't3:a', 't3', 't4'] == self.cleaned

    def test_clean_default(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               sel_tasks=['t1'], dep_manager=mock.MagicMock())
        cmd_clean._execute(False, False, False, False)
        # default enable --clean-dep by default
        assert ['t2', 't1'] == self.cleaned

    def test_clean_default_all(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(False, False, False, False)
        # default enable --clean-dep by default
        assert set(['t1','t2', 't3:a', 't3', 't4']) == set(self.cleaned)

    def test_clean_selected(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(False, False, False, False, ['t2'])
        assert ['t2'] == self.cleaned
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(False, True, False, False, ['t1'])
        assert ['t2', 't1'] == self.cleaned
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep_recursive(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(False, True, False, False, ['t4'])
        assert ['t2', 't1', 't4'] == self.cleaned

    def test_clean_subtasks(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(False, False, False, False, ['t3'])
        assert ['t3:a', 't3'] == self.cleaned

    def test_clean_taskdep_once(self, tasks):
        # do not execute clean operation more than once
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(False, True, False, False, ['t1', 't2'])
        assert ['t2', 't1'] == self.cleaned

    def test_clean_invalid_task(self, tasks):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               sel_tasks=['t1'])
        pytest.raises(InvalidCommand, cmd_clean._execute,
                      False, False, False, False, ['xxxx'])

    def test_clean_forget_selected(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(False, False, False, True, ['t2'])
        assert ['t2'] == self.cleaned
        mock_dep_manager.assert_has_calls([mock.call.remove(mock.ANY), mock.call.close()])  # order
        assert mock_dep_manager.remove.call_args_list == [mock.call('t2')]  # exactly t2, not more

    def test_clean_forget_taskdep(self, tasks):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(False, True, False, True, ['t1'])
        assert ['t2', 't1'] == self.cleaned
        mock_dep_manager.assert_has_calls([mock.call.remove(mock.ANY), mock.call.close()])  # order
        assert mock_dep_manager.remove.call_args_list == [mock.call('t2'), mock.call('t1')]
