import pytest
from mock import Mock

from doit import get_var
from doit.exceptions import InvalidCommand
from doit import doit_cmd
from doit import loader


def mock_get_tasks(*args, **kwargs):
    return {'task_list': ['a','b','c'],
            'config': {'default_tasks': ['a','c']},
            }

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
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_run = Mock()
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_run)
        doit_cmd.cmd_main([])
        assert 1 == mock_run.call_count

    def test_run_other_subcommand(self, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_list = Mock()
        monkeypatch.setattr(doit_cmd.List, "execute", mock_list)
        doit_cmd.cmd_main(["list"])
        assert 1 == mock_list.call_count

    def test_cmdline_vars(self, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_run = Mock()
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_run)
        doit_cmd.cmd_main(['x=1', 'y=abc'])
        assert '1' == get_var('x')
        assert 'abc' == get_var('y')

    def test_cmdline_vars_not_opts(self, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_run = Mock()
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_run)
        doit_cmd.cmd_main(['--z=5'])
        assert None == get_var('--z')



class TestErrors(object):
    def test_interrupt(self, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        def my_raise(*args):
            raise KeyboardInterrupt()
        mock_cmd = Mock(side_effect=my_raise)
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_cmd)
        pytest.raises(KeyboardInterrupt, doit_cmd.cmd_main, [])

    def test_user_error(self, capsys, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_cmd = Mock(side_effect=InvalidCommand)
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_cmd)
        got = doit_cmd.cmd_main([])
        assert 3 == got
        out, err = capsys.readouterr()
        assert "ERROR" in err

    def test_internal_error(self, capsys, monkeypatch):
        monkeypatch.setattr(loader, "get_tasks", mock_get_tasks)
        mock_cmd = Mock(side_effect=Exception)
        monkeypatch.setattr(doit_cmd.Run, "execute", mock_cmd)
        got = doit_cmd.cmd_main([])
        assert 3 == got
        out, err = capsys.readouterr()
        # traceback from Exception (this case code from mock lib)
        assert "mock.py" in err

