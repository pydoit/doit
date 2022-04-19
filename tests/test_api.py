import sys

from doit.cmd_base import ModuleTaskLoader
from doit.api import run, run_tasks


def test_run(monkeypatch, depfile_name):
    monkeypatch.setattr(sys, 'argv', ['did', '--db-file', depfile_name])
    try:
        def hi():
            print('hi')
        def task_hi():
            return {'actions': [hi]}
        run(locals())
    except SystemExit as err:
        assert err.code == 0
    else: # pragma: no cover
        assert False



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


def test_run_tasks_success(capsys, depfile_name):
    result = run_tasks(
        ModuleTaskLoader(_dodo()),
        {'hi': {'opt': '3'}},
        extra_config = {
            'GLOBAL': {
                'verbosity': 2,
                'dep_file': depfile_name,
            },
        },
    )
    assert result == 0
    out = capsys.readouterr().out
    assert out.strip() == 'hi 3'


def test_run_tasks_error(capsys, depfile_name):
    result = run_tasks(
        ModuleTaskLoader(_dodo()),
        {'two': None},
        extra_config = {
            'GLOBAL': {
                'verbosity': 2,
                'dep_file': depfile_name,
            },
        },
    )
    assert result == 1




def test_run_tasks_pos(capsys, depfile_name):
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
            'dep_file': depfile_name,
        },
    }
    result = run_tasks(ModuleTaskLoader(_dodo_pos()), tasks_selection, extra_config=extra_config)
    assert result == 0
    out = capsys.readouterr().out
    assert out.strip() == 'hi:3--foo bar baz'
