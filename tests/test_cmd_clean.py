import unittest
import contextlib
import sys
from io import StringIO
from unittest import mock

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_clean import Clean
from tests.support import CmdFactory


class TestCmdClean(unittest.TestCase):

    def test_failure_exit_status_and_remaining_tasks(self):
        cleaned = []
        def fail_clean():
            return False
        def later_clean():
            cleaned.append(True)
        tasks = [Task('bad', None, clean=[fail_clean]),
                 Task('good', None, clean=[later_clean])]
        manager = mock.MagicMock()
        command = CmdFactory(Clean, outstream=StringIO(), task_list=tasks,
                             dep_manager=manager)
        with contextlib.redirect_stderr(StringIO()):
            result = command._execute(dryrun=False, cleandep=False,
                                      cleanall=False, cleanforget=False,
                                      pos_args=['bad', 'good'])
        self.assertEqual(1, result)
        self.assertEqual([True], cleaned)
        manager.close.assert_called_once_with()

    def test_command_failure_and_dry_run_status(self):
        action = '"%s" -c "raise SystemExit(3)"' % sys.executable
        tasks = [Task('bad', None, clean=[action])]
        for dryrun, expected in [(True, 0), (False, 1)]:
            with self.subTest(dryrun=dryrun):
                command = CmdFactory(Clean, outstream=StringIO(), task_list=tasks,
                                     dep_manager=mock.MagicMock())
                with contextlib.redirect_stderr(StringIO()):
                    result = command._execute(dryrun=dryrun, cleandep=False,
                                              cleanall=False, cleanforget=False,
                                              pos_args=['bad'])
                self.assertEqual(expected, result)

    def setUp(self):
        super().setUp()
        self.cleaned = []
        def myclean(name):
            self.cleaned.append(name)
        self.tasks = [
            Task("t1", None, targets=['t1.out'], setup=['t2'],
                 clean=[(myclean,('t1',))]),
            Task("t2", None, clean=[(myclean,('t2',))]),
            Task("t3", None, task_dep=['t3:a'], has_subtask=True,
                 clean=[(myclean,('t3',))]),
            Task("t3:a", None, clean=[(myclean,('t3:a',))], subtask_of='t3'),
            Task("t4", None, file_dep=['t1.out'], clean=[(myclean,('t4',))]),
        ]

    def test_clean_all(self):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=True,
                           cleanforget=False)
        # all enables --clean-dep
        self.assertEqual(['t4', 't1', 't2', 't3', 't3:a'], self.cleaned)

    def test_clean_default_all(self):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False)
        # default enables --clean-dep
        self.assertEqual(['t4', 't1', 't2', 't3', 't3:a'], self.cleaned)

    def test_clean_default(self):
        output = StringIO()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=self.tasks,
            sel_tasks=['t1'], dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False)
        # default enables --clean-dep
        self.assertEqual(['t1', 't2'], self.cleaned)

    def test_clean_all_ignores_default(self):
        output = StringIO()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=self.tasks,
            sel_tasks=['t1'], dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=True,
                           cleanforget=False)
        # default enables --clean-dep
        self.assertEqual(['t4', 't1', 't2', 't3', 't3:a'], self.cleaned)

    def test_clean_selected(self):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=self.tasks,
            sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False, pos_args=['t2'])
        self.assertEqual(['t2'], self.cleaned)
        mock_dep_manager.remove.assert_not_called()

    def test_clean_selected_wildcard(self):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=self.tasks,
            dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False, pos_args=['t3*'])
        self.assertEqual(['t3', 't3:a'], self.cleaned)
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep(self):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t1'])
        self.assertEqual(['t1', 't2'], self.cleaned)
        mock_dep_manager.remove.assert_not_called()

    def test_clean_taskdep_recursive(self):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t4'])
        self.assertEqual(['t4', 't1', 't2'], self.cleaned)

    def test_clean_subtasks(self):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=False, pos_args=['t3'])
        self.assertEqual(['t3', 't3:a'], self.cleaned)

    def test_clean_taskdep_once(self):
        # do not execute clean operation more than once
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock.MagicMock())
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=False, pos_args=['t1', 't2'])
        self.assertEqual(['t1', 't2'], self.cleaned)

    def test_clean_invalid_task(self):
        output = StringIO()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               sel_tasks=['t1'])
        self.assertRaises(InvalidCommand, cmd_clean._execute,
                          dryrun=False, cleandep=False, cleanall=False,
                          cleanforget=False, pos_args=['xxxx'])

    def test_clean_forget_selected(self):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(
            Clean, outstream=output, task_list=self.tasks,
            sel_tasks=['t1'], dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=False, cleanall=False,
                           cleanforget=True, pos_args=['t2'])
        self.assertEqual(['t2'], self.cleaned)
        # order
        mock_dep_manager.assert_has_calls(
            [mock.call.remove(mock.ANY), mock.call.close()])
        # exactly t2, not more
        self.assertEqual(mock_dep_manager.remove.call_args_list,
                         [mock.call('t2')])

    def test_clean_forget_taskdep(self):
        output = StringIO()
        mock_dep_manager = mock.MagicMock()
        cmd_clean = CmdFactory(Clean, outstream=output, task_list=self.tasks,
                               dep_manager=mock_dep_manager)
        cmd_clean._execute(dryrun=False, cleandep=True, cleanall=False,
                           cleanforget=True, pos_args=['t1'])
        self.assertEqual(['t1', 't2'], self.cleaned)
        # order
        mock_dep_manager.assert_has_calls(
            [mock.call.remove(mock.ANY), mock.call.close()])
        self.assertEqual(mock_dep_manager.remove.call_args_list,
                         [mock.call('t1'), mock.call('t2')])
