import sys
import inspect

import py.test
from mock import Mock

from doit import doit_cmd
from doit import main


def mock_get_tasks(*args, **kwargs):
    return {'default_tasks': ['a','c'],
            'task_list': ['a','b','c']}

class TestRun(object):
    def test_version(self, capsys):
        doit_cmd.cmd_main(["--version"])
        out, err = capsys.readouterr()
        assert "bin" in out
        assert "lib" in out

    def test_usage(self, capsys):
        doit_cmd.cmd_main(["--help"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_usage(self, capsys):
        doit_cmd.cmd_main(["help"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_task(self, capsys):
        doit_cmd.cmd_main(["help", "task"])
        out, err = capsys.readouterr()
        assert "Task Dictionary parameters" in out

    def test_help_cmd(self, capsys):
        doit_cmd.cmd_main(["help", "list"])
        out, err = capsys.readouterr()
        assert "Purpose: list tasks from dodo file" in out

    def test_run_is_default(self, monkeypatch):
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_run = Mock()
        monkeypatch.setattr(doit_cmd, "doit_run", mock_run)
        doit_cmd.cmd_main([])
        assert 1 == mock_run.call_count

    def test_run_other_subcommand(self, monkeypatch):
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_list = Mock()
        monkeypatch.setattr(doit_cmd, "doit_list", mock_list)
        doit_cmd.cmd_main(["list"])
        assert 1 == mock_list.call_count


class TestInterface(object):
    def test_doit_run_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_run)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_run = Mock()
        monkeypatch.setattr(doit_cmd, "doit_run", mock_run)
        doit_cmd.cmd_main(["--output-file", "mylog.txt",
                                 "-v2", "--continue", "--reporter", "myr"])

        expected = [('dependencyFile', '.doit.db'),
                    ('task_list', mock_get_tasks()['task_list']),
                    ('output', 'mylog.txt'),
                    ('options', mock_get_tasks()['default_tasks']),
                    ('verbosity', 2),
                    ('alwaysExecute', False),
                    ('continue_', True),
                    ('reporter', "myr"),]

        assert len(expected) == len(argspec[0])
        assert len(expected) == len(mock_run.call_args[0])
        for exp,got in zip(expected, zip(argspec[0], mock_run.call_args[0])):
            assert exp == got


    def test_doit_list_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_list)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_list = Mock()
        monkeypatch.setattr(doit_cmd, "doit_list", mock_list)
        doit_cmd.cmd_main(["list", "--all", "--quiet", "--status", "c", "a"])
        assert mock_list.called

        expected = [('dependencyFile', '.doit.db'),
                    ('task_list', mock_get_tasks()['task_list']),
                    ('outstream', sys.stdout),
                    ('filter_tasks', ["c", "a"]),
                    ('print_subtasks', True),
                    ('print_doc', False),
                    ('print_status', True),
                    ('print_private', False),]

        assert len(expected) == len(argspec[0])
        assert len(expected) == len(mock_list.call_args[0])
        for exp,got in zip(expected, zip(argspec[0], mock_list.call_args[0])):
            assert exp == got


    def test_doit_clean_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_clean)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_clean = Mock()
        monkeypatch.setattr(doit_cmd, "doit_clean", mock_clean)
        doit_cmd.cmd_main(["clean", "--dry-run"])
        assert mock_clean.called

        expected = [('task_list', mock_get_tasks()['task_list']),
                    ('outstream', sys.stdout),
                    ('dryrun', True),
                    ('clean_dep', False),
                    ('clean_tasks', mock_get_tasks()['default_tasks']),]


        assert len(expected) == len(argspec[0])
        assert len(expected) == len(mock_clean.call_args[0])
        for exp,got in zip(expected, zip(argspec[0], mock_clean.call_args[0])):
            assert exp == got


    def test_doit_forget_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_forget)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_forget = Mock()
        monkeypatch.setattr(doit_cmd, "doit_forget", mock_forget)
        doit_cmd.cmd_main(["forget",])

        expected = [('dependencyFile', '.doit.db'),
                    ('task_list', mock_get_tasks()['task_list']),
                    ('outstream', sys.stdout),
                    ('forgetTasks', mock_get_tasks()['default_tasks']),
                    ]

        assert len(expected) == len(argspec[0])
        assert len(expected) == len(mock_forget.call_args[0])
        for exp,got in zip(expected, zip(argspec[0], mock_forget.call_args[0])):
            assert exp == got


    def test_doit_ignore_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_ignore)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_ignore = Mock()
        monkeypatch.setattr(doit_cmd, "doit_ignore", mock_ignore)
        doit_cmd.cmd_main(["ignore", "b"])

        expected = [('dependencyFile', '.doit.db'),
                    ('task_list', mock_get_tasks()['task_list']),
                    ('outstream', sys.stdout),
                    ('ignoreTasks', ['b']),
                    ]

        assert len(expected) == len(argspec[0])
        assert len(expected) == len(mock_ignore.call_args[0])
        for exp,got in zip(expected, zip(argspec[0], mock_ignore.call_args[0])):
            assert exp == got


    def test_doit_auto_args(self, monkeypatch):
        argspec = inspect.getargspec(doit_cmd.doit_auto)
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_auto = Mock()
        monkeypatch.setattr(doit_cmd, "doit_auto", mock_auto)
        doit_cmd.cmd_main(["auto", "b"])

        expected = [('dependency_file', '.doit.db'),
                    ('task_list', mock_get_tasks()['task_list']),
                    ('filter_tasks', ['b']),
                    ('loop_callback', None),
                    ]

        assert len(expected) == len(argspec[0])
        #                                                    + loop_callback
        assert len(expected) == (len(mock_auto.call_args[0]) + 1)
        for exp,got in zip(expected, zip(argspec[0], mock_auto.call_args[0])):
            assert exp == got


class TestErrors(object):
    def test_interrupt(self, monkeypatch):
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        def my_raise(*args):
            raise KeyboardInterrupt()
        mock_cmd = Mock(side_effect=my_raise)
        monkeypatch.setattr(doit_cmd, "doit_run", mock_cmd)
        py.test.raises(KeyboardInterrupt, doit_cmd.cmd_main, [])

    def test_user_error(self, capsys, monkeypatch):
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_cmd = Mock(side_effect=main.InvalidCommand)
        monkeypatch.setattr(doit_cmd, "doit_run", mock_cmd)
        got = doit_cmd.cmd_main([])
        assert 1 == got
        out, err = capsys.readouterr()
        assert "ERROR" in out

    def test_internal_error(self, capsys, monkeypatch):
        monkeypatch.setattr(main, "get_tasks", mock_get_tasks)
        mock_cmd = Mock(side_effect=Exception)
        monkeypatch.setattr(doit_cmd, "doit_run", mock_cmd)
        got = doit_cmd.cmd_main([])
        assert 1 == got
        # FIXME I cant test output because sys.__stderr__ is used...
