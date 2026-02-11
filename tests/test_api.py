import io
import sys
import unittest
import contextlib
from unittest.mock import patch

from doit.cmd_base import ModuleTaskLoader
from doit.api import run, run_tasks
from tests.support import DepfileNameMixin


class TestRun(DepfileNameMixin, unittest.TestCase):
    def test_run(self):
        with patch.object(sys, 'argv', ['did', '--db-file', self.depfile_name]):
            try:
                def hi():
                    print('hi')
                def task_hi():
                    return {'actions': [hi]}
                run(locals())
            except SystemExit as err:
                self.assertEqual(0, err.code)
            else:  # pragma: no cover
                self.fail("SystemExit not raised")


def _dodo():
    """sample tasks"""
    def hi(opt=None):
        print('hi', opt)

    def task_hi():
        return {
            'actions': [hi],
            'params': [{'name': 'opt', 'default': '1'}],
        }
    def task_two():
        def my_error():
            return False
        return {
            'actions': [my_error],
        }

    return {
        'task_hi': task_hi,
        'task_two': task_two,
    }


class TestRunTasks(DepfileNameMixin, unittest.TestCase):
    def test_run_tasks_success(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = run_tasks(
                ModuleTaskLoader(_dodo()),
                {'hi': {'opt': '3'}},
                extra_config={
                    'GLOBAL': {
                        'verbosity': 2,
                        'dep_file': self.depfile_name,
                    },
                },
            )
        self.assertEqual(0, result)
        self.assertEqual('hi 3', out.getvalue().strip())

    def test_run_tasks_error(self):
        result = run_tasks(
            ModuleTaskLoader(_dodo()),
            {'two': None},
            extra_config={
                'GLOBAL': {
                    'verbosity': 2,
                    'dep_file': self.depfile_name,
                },
            },
        )
        self.assertEqual(1, result)

    def test_run_tasks_pos(self):
        def _dodo_pos():
            """sample tasks"""
            def hi(opt, pos):
                print(f'hi:{opt}--{pos}')

            def task_hi():
                return {
                    'actions': [hi],
                    'params': [{'name': 'opt', 'default': '1'}],
                    'pos_arg': 'pos',
                }
            return {
                'task_hi': task_hi,
            }

        tasks_selection = {'hi': {'opt': '3', 'pos': 'foo bar baz'}}
        extra_config = {
            'GLOBAL': {
                'verbosity': 2,
                'dep_file': self.depfile_name,
            },
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = run_tasks(ModuleTaskLoader(_dodo_pos()),
                               tasks_selection, extra_config=extra_config)
        self.assertEqual(0, result)
        self.assertEqual('hi:3--foo bar baz', out.getvalue().strip())
