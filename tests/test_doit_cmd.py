import io
import os
import unittest
import contextlib
import tempfile
import shutil
from unittest.mock import Mock, patch

from doit.exceptions import InvalidCommand
from doit.cmd_run import Run
from doit.cmd_list import List
from doit import doit_cmd
from tests.support import DepfileNameMixin


def cmd_main(args):
    main = doit_cmd.DoitMain()
    main.BIN_NAME = 'doit'
    return main.run(args)


class TestRun(unittest.TestCase):
    def test_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cmd_main(["--version"])
        self.assertIn("lib", out.getvalue())

    def test_usage(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cmd_main(["--help"])
        self.assertIn("doit list", out.getvalue())

    def test_run_is_default(self):
        mock_run = Mock()
        with patch.object(Run, "execute", mock_run):
            cmd_main([])
        self.assertEqual(1, mock_run.call_count)

    def test_run_other_subcommand(self):
        mock_list = Mock()
        with patch.object(List, "execute", mock_list):
            cmd_main(["list"])
        self.assertEqual(1, mock_list.call_count)

    def test_cmdline_vars(self):
        mock_run = Mock()
        with patch.object(Run, "execute", mock_run):
            cmd_main(['x=1', 'y=abc'])
        self.assertEqual('1', doit_cmd.get_var('x'))
        self.assertEqual('abc', doit_cmd.get_var('y'))
        self.assertIsNone(doit_cmd.get_var('z'))

    def test_cmdline_novars(self):
        mock_run = Mock()
        with patch.object(Run, "execute", mock_run):
            cmd_main(['x=1'])
        doit_cmd._CMDLINE_VARS = None
        self.assertIsNone(doit_cmd.get_var('x'))

    def test_cmdline_vars_not_opts(self):
        mock_run = Mock()
        with patch.object(Run, "execute", mock_run):
            cmd_main(['--z=5'])
        self.assertIsNone(doit_cmd.get_var('--z'))

    def test_cmdline_loader_option_before_cmd_name(self):
        mock_list = Mock()
        with patch.object(List, "execute", mock_list):
            cmd_main(['-k', 'list', '--all'])
        self.assertTrue(mock_list.called)
        params, args = mock_list.call_args[0]
        self.assertTrue(params['subtasks'])
        self.assertTrue(params['seek_file'])
        self.assertEqual([], args)

    def test_cmdline_loader_option_mixed(self):
        mock_run = Mock()
        with patch.object(Run, "execute", mock_run):
            cmd_main(['-c', '-k', 'lala'])
        self.assertTrue(mock_run.called)
        params, args = mock_run.call_args[0]
        self.assertTrue(params['continue'])
        self.assertTrue(params['seek_file'])
        self.assertEqual(['lala'], args)

    def test_task_loader_has_cmd_list(self):
        cmd_names = []
        def save_cmd_names(self, params, args):
            cmd_names.extend(self.loader.cmd_names)
        with patch.object(Run, "execute", save_cmd_names):
            cmd_main([])
        self.assertIn('list', cmd_names)


class TestRunExtraConfig(DepfileNameMixin, unittest.TestCase):
    def test_extra_config(self):
        outfile_val = []
        def monkey_run(self, opt_values, pos_args):
            outfile_val.append(opt_values['outfile'])
        with patch.object(Run, "execute", monkey_run):
            extra_config = {
                'outfile': 'foo.txt',
                'dep_file': self.depfile_name,
            }
            doit_cmd.DoitMain(extra_config={'GLOBAL': extra_config}).run([])
        self.assertEqual('foo.txt', outfile_val[0])


class TestErrors(unittest.TestCase):
    def test_interrupt(self):
        def my_raise(*args):
            raise KeyboardInterrupt()
        mock_cmd = Mock(side_effect=my_raise)
        with patch.object(Run, "execute", mock_cmd):
            self.assertRaises(KeyboardInterrupt, cmd_main, [])

    def test_user_error(self):
        mock_cmd = Mock(side_effect=InvalidCommand)
        err = io.StringIO()
        with patch.object(Run, "execute", mock_cmd), \
             contextlib.redirect_stderr(err):
            got = cmd_main([])
        self.assertEqual(3, got)
        self.assertIn("ERROR", err.getvalue())

    def test_internal_error(self):
        mock_cmd = Mock(side_effect=Exception)
        err = io.StringIO()
        with patch.object(Run, "execute", mock_cmd), \
             contextlib.redirect_stderr(err):
            got = cmd_main([])
        self.assertEqual(3, got)
        self.assertIn("mock.py", err.getvalue())


class TestConfig(unittest.TestCase):
    def _test_path(self, filename):
        return os.path.join(os.path.dirname(__file__), '..', 'tests', filename)

    def test_no_ini_config_file(self):
        main = doit_cmd.DoitMain(config_filenames=())
        main.run(['--version'])

    def test_load_plugins_command(self):
        config_filename = self._test_path('sample.cfg')
        main = doit_cmd.DoitMain(config_filenames=config_filename)
        self.assertEqual(1, len(main.config['COMMAND']))
        self.assertIn('foo', main.get_cmds())

    def test_merge_api_ini_config(self):
        config_filename = self._test_path('sample.cfg')
        api_config = {'GLOBAL': {'opty': '10', 'optz': '10'}}
        main = doit_cmd.DoitMain(config_filenames=config_filename,
                                 extra_config=api_config)
        self.assertEqual(1, len(main.config['COMMAND']))
        self.assertIn('foo', main.get_cmds())
        self.assertEqual({'optx': '6', 'opty': '7', 'optz': '10'},
                         main.config['GLOBAL'])

    def test_execute_command_plugin(self):
        config_filename = self._test_path('sample.cfg')
        main = doit_cmd.DoitMain(config_filenames=config_filename)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main.run(['foo'])
        self.assertEqual('this command does nothing!\n', out.getvalue())

    def test_merge_api_toml_config(self):
        config_filename = self._test_path('sample.toml')
        api_config = {'GLOBAL': {'opty': '10', 'optz': '10'}}
        main = doit_cmd.DoitMain(config_filenames=config_filename,
                                 extra_config=api_config)
        self.assertEqual(1, len(main.config['COMMAND']))
        self.assertIn('foo', main.get_cmds())
        self.assertEqual({'optx': '6', 'opty': '7', 'optz': '10'},
                         main.config['GLOBAL'])
        self.assertEqual({'nval': 33}, main.config['foo'])
        self.assertEqual({'opt': "baz"}, main.config['task:bar'])

    def test_find_pyproject_toml_config(self):
        config_filename = self._test_path('pyproject.toml')
        api_config = {'GLOBAL': {'opty': '10', 'optz': '10'}}

        with tempfile.TemporaryDirectory() as td:
            shutil.copy(config_filename, os.path.join(td, 'pyproject.toml'))
            old_cwd = os.getcwd()
            try:
                os.chdir(td)
                main = doit_cmd.DoitMain(extra_config=api_config)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(1, len(main.config['COMMAND']))
            self.assertIn('bar', main.get_cmds())
            self.assertEqual({'optx': '2', 'opty': '3', 'optz': '10'},
                             main.config['GLOBAL'])
