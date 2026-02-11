import io
import unittest
import contextlib

from doit.doit_cmd import DoitMain
from tests.support import RestoreCwdMixin, DepfileNameMixin


def cmd_main(args, extra_config=None, bin_name='doit'):
    if extra_config:
        extra_config = {'GLOBAL': extra_config}
    main = DoitMain(extra_config=extra_config)
    main.BIN_NAME = bin_name
    return main.run(args)


class TestHelp(unittest.TestCase):
    def _run(self, args, extra_config=None, bin_name='doit'):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            returned = cmd_main(args, extra_config, bin_name)
        return returned, out.getvalue(), err.getvalue()

    def test_help_usage(self):
        returned, out, err = self._run(["help"])
        self.assertEqual(0, returned)
        self.assertIn("doit list", out)

    def test_help_usage_custom_name(self):
        returned, out, err = self._run(["help"], bin_name='mytool')
        self.assertEqual(0, returned)
        self.assertIn("mytool list", out)

    def test_help_plugin_name(self):
        plugin = {'XXX': 'tests.sample_plugin:MyCmd'}
        main = DoitMain(extra_config={'COMMAND':plugin})
        main.BIN_NAME = 'doit'
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            returned = main.run(["help"])
        self.assertEqual(0, returned)
        self.assertIn("doit XXX ", out.getvalue())
        self.assertIn("test extending doit commands", out.getvalue())

    def test_help_task_params(self):
        returned, out, err = self._run(["help", "task"])
        self.assertEqual(0, returned)
        self.assertIn("Task Dictionary parameters", out)

    def test_help_cmd(self):
        returned, out, err = self._run(["help", "list"], {'dep_file': 'foo.db'})
        self.assertEqual(0, returned)
        self.assertIn("PURPOSE", out)
        self.assertIn("list tasks from dodo file", out)
        # overwritten defaults, are shown as default
        self.assertIn("file used to save successful runs [default: foo.db]", out)


class TestHelpWithLoader(RestoreCwdMixin, DepfileNameMixin, unittest.TestCase):
    def _run(self, args, extra_config=None, bin_name='doit'):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            returned = cmd_main(args, extra_config, bin_name)
        return returned, out.getvalue(), err.getvalue()

    def test_help_task_name(self):
        returned, out, err = self._run(["help", "-f", "tests/loader_sample.py",
                                        "--db-file", self.depfile_name, "xxx1"])
        self.assertEqual(0, returned)
        self.assertIn("xxx1", out)  # name
        self.assertIn("task doc", out)  # doc
        self.assertIn("-p", out)  # params

    def test_help_wrong_name(self):
        returned, out, err = self._run(["help", "-f", "tests/loader_sample.py",
                                        "--db-file", self.depfile_name, "wrong_name"])
        self.assertEqual(0, returned)  # TODO return different value?
        self.assertIn("doit list", out)

    def test_help_no_dodo_file(self):
        returned, out, err = self._run(["help", "-f", "no_dodo", "wrong_name"])
        self.assertEqual(0, returned)  # TODO return different value?
        self.assertIn("doit list", out)
