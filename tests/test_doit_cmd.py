import os
from unittest.mock import Mock

import pytest

from doit.exceptions import InvalidCommand
from doit.cmd_run import Run
from doit.cmd_list import List
from doit import doit_cmd



def cmd_main(args):
    main = doit_cmd.DoitMain()
    main.BIN_NAME = 'doit'
    return main.run(args)


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
        assert '1' == doit_cmd.get_var('x')
        assert 'abc' == doit_cmd.get_var('y')
        assert None is doit_cmd.get_var('z')

    def test_cmdline_novars(self, monkeypatch):
        mock_run = Mock()
        monkeypatch.setattr(Run, "execute", mock_run)
        cmd_main(['x=1'])

        # Simulate the variable below not being initialized by a subprocess on
        # Windows. See https://github.com/pydoit/doit/issues/164.
        doit_cmd._CMDLINE_VARS = None
        assert None is doit_cmd.get_var('x')

    def test_cmdline_vars_not_opts(self, monkeypatch):
        mock_run = Mock()
        monkeypatch.setattr(Run, "execute", mock_run)
        cmd_main(['--z=5'])
        assert None == doit_cmd.get_var('--z')

    def test_task_loader_has_cmd_list(self, monkeypatch):
        cmd_names = []
        def save_cmd_names(self, params, args):
            cmd_names.extend(self.loader.cmd_names)
        monkeypatch.setattr(Run, "execute", save_cmd_names)
        cmd_main([])
        assert 'list' in cmd_names

    def test_extra_config(self, monkeypatch, depfile_name):
        outfile_val = []
        def monkey_run(self, opt_values, pos_args):
            outfile_val.append(opt_values['outfile'])
        monkeypatch.setattr(Run, "execute", monkey_run)
        extra_config = {
            'outfile': 'foo.txt',
            'dep_file': depfile_name,
        }
        doit_cmd.DoitMain(extra_config={'GLOBAL': extra_config}).run([])
        assert outfile_val[0] == 'foo.txt'



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


class TestConfig(object):
    def test_no_ini_config_file(self):
        main = doit_cmd.DoitMain(config_filenames=())
        main.run(['--version'])

    def test_load_plugins_command(self):
        config_filename = os.path.join(os.path.dirname(__file__), 'sample.cfg')
        main = doit_cmd.DoitMain(config_filenames=config_filename)
        assert 1 == len(main.config['COMMAND'])
        # test loaded plugin command is actually used with plugin name
        assert 'foo' in main.get_cmds()

    def test_merge_api_ini_config(self):
        config_filename = os.path.join(os.path.dirname(__file__), 'sample.cfg')
        api_config = {'GLOBAL': {'opty':'10', 'optz':'10'}}
        main = doit_cmd.DoitMain(config_filenames=config_filename,
                                 extra_config=api_config)
        assert 1 == len(main.config['COMMAND'])
        # test loaded plugin command is actually used with plugin name
        assert 'foo' in main.get_cmds()
        # INI has higher preference the api_config
        assert main.config['GLOBAL'] == {'optx':'6', 'opty':'7', 'optz':'10'}

    def test_execute_command_plugin(self, capsys):
        config_filename = os.path.join(os.path.dirname(__file__), 'sample.cfg')
        main = doit_cmd.DoitMain(config_filenames=config_filename)
        main.run(['foo'])
        got = capsys.readouterr()[0]
        assert got == 'this command does nothing!\n'
