import os

import pytest
from mock import Mock

from doit import get_var
from doit.exceptions import InvalidCommand
from doit.cmd_run import Run
from doit.cmd_list import List
from doit import doit_cmd



class TestPluginRegistry(object):
    def test_get_empty_list_for_whatever_category(self):
        plugins = doit_cmd.PluginRegistry()
        assert [] == plugins['foo']
        assert [] == plugins['whatever name']

    def test_add_many(self):
        plugins = doit_cmd.PluginRegistry()
        plugins.add('category1', 'pytest', 'raises')
        plugins.add('category1', 'mock', 'Mock')
        plugins.add('category2', 'doit.cmd_run', 'Run')
        assert 2 == len(plugins['category1'])
        assert pytest.raises is plugins['category1'][0]
        assert Mock is plugins['category1'][1]
        assert 1 == len(plugins['category2'])
        assert Run is plugins['category2'][0]


class TestLoadINI(object):
    def test_load_plugins_command(self):
        config_filename = os.path.join(os.path.dirname(__file__), 'sample.cfg')
        main = doit_cmd.DoitMain(config_filenames=config_filename)
        assert 1 == len(main.plugins['command'])
        assert main.plugins['command'][0].name == 'mycmd'
        # test loaded plugin command is actually used
        assert 'mycmd' in main.get_commands()


def cmd_main(args):
    return doit_cmd.DoitMain().run(args)


class TestRun(object):
    def test_version(self, capsys):
        cmd_main(["--version"])
        out, err = capsys.readouterr()
        assert "lib" in out

    def test_usage(self, capsys):
        cmd_main(["--help"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_run_is_default(self, monkeypatch):
        mock_run = Mock()
        monkeypatch.setattr(Run, "execute", mock_run)
        cmd_main([])
        assert 1 == mock_run.call_count

    def test_run_other_subcommand(self, monkeypatch):
        mock_list = Mock()
        monkeypatch.setattr(List, "execute", mock_list)
        cmd_main(["list"])
        assert 1 == mock_list.call_count

    def test_cmdline_vars(self, monkeypatch):
        mock_run = Mock()
        monkeypatch.setattr(Run, "execute", mock_run)
        cmd_main(['x=1', 'y=abc'])
        assert '1' == get_var('x')
        assert 'abc' == get_var('y')

    def test_cmdline_vars_not_opts(self, monkeypatch):
        mock_run = Mock()
        monkeypatch.setattr(Run, "execute", mock_run)
        cmd_main(['--z=5'])
        assert None == get_var('--z')



class TestErrors(object):
    def test_interrupt(self, monkeypatch):
        def my_raise(*args):
            raise KeyboardInterrupt()
        mock_cmd = Mock(side_effect=my_raise)
        monkeypatch.setattr(Run, "execute", mock_cmd)
        pytest.raises(KeyboardInterrupt, cmd_main, [])

    def test_user_error(self, capsys, monkeypatch):
        mock_cmd = Mock(side_effect=InvalidCommand)
        monkeypatch.setattr(Run, "execute", mock_cmd)
        got = cmd_main([])
        assert 3 == got
        out, err = capsys.readouterr()
        assert "ERROR" in err

    def test_internal_error(self, capsys, monkeypatch):
        mock_cmd = Mock(side_effect=Exception)
        monkeypatch.setattr(Run, "execute", mock_cmd)
        got = cmd_main([])
        assert 3 == got
        out, err = capsys.readouterr()
        # traceback from Exception (this case code from mock lib)
        assert "mock.py" in err

