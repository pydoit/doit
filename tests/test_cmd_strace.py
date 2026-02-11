import os
import os.path
import sys
import unittest
from io import StringIO

from doit.cmd_base import TaskLoader2
from doit.exceptions import InvalidCommand
from doit.cmdparse import DefaultUpdate
from doit.dependency import JSONCodec
from doit.task import Task
from doit.cmd_strace import Strace
from tests.support import CmdFactory, DepfileNameMixin, DependencyFileMixin


@unittest.skipIf(
    os.system('strace -V') != 0 or sys.platform in ['win32', 'cygwin'],
    'strace not available or Windows platform')
class TestCmdStrace(DependencyFileMixin, DepfileNameMixin, unittest.TestCase):

    @staticmethod
    def loader_for_task(task):

        class MyTaskLoader(TaskLoader2):
            def load_doit_config(self):
                return {}

            def load_tasks(self, cmd, pos_args):
                return [task]

        return MyTaskLoader()

    def test_dep(self):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Strace, outstream=output)
        cmd.loader = self.loader_for_task(task)
        params = DefaultUpdate(dep_file=self.depfile_name, show_all=False,
                               keep_trace=False, backend='dbm',
                               check_file_uptodate='md5', codec_cls=JSONCodec)
        result = cmd.execute(params, ['tt'])
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")
        dep_path = os.path.abspath("tests/data/dependency1")
        self.assertIn("R %s" % dep_path, got)

    def test_opt_show_all(self):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Strace, outstream=output)
        cmd.loader = self.loader_for_task(task)
        params = DefaultUpdate(dep_file=self.depfile_name, show_all=True,
                               keep_trace=False, backend='dbm',
                               check_file_uptodate='md5', codec_cls=JSONCodec)
        result = cmd.execute(params, ['tt'])
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")
        self.assertIn("cat", got[0])

    def test_opt_keep_trace(self):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Strace, outstream=output)
        cmd.loader = self.loader_for_task(task)
        params = DefaultUpdate(dep_file=self.depfile_name, show_all=True,
                               keep_trace=True, backend='dbm',
                               check_file_uptodate='md5', codec_cls=JSONCodec)
        result = cmd.execute(params, ['tt'])
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")
        self.assertIn("cat", got[0])
        self.assertTrue(os.path.exists(cmd.TRACE_OUT))
        os.unlink(cmd.TRACE_OUT)

    def test_target(self):
        output = StringIO()
        task = Task("tt", ["touch %(targets)s"],
                    targets=['tests/data/dependency1'])
        cmd = CmdFactory(Strace, outstream=output)
        cmd.loader = self.loader_for_task(task)
        params = DefaultUpdate(dep_file=self.depfile_name, show_all=False,
                               keep_trace=False, backend='dbm',
                               check_file_uptodate='md5', codec_cls=JSONCodec)
        result = cmd.execute(params, ['tt'])
        self.assertEqual(0, result)
        got = output.getvalue().split("\n")
        tgt_path = os.path.abspath("tests/data/dependency1")
        self.assertIn("W %s" % tgt_path, got)

    def test_ignore_python_actions(self):
        output = StringIO()
        dep1 = self.dependency1
        def py_open():
            with open(dep1) as ignore:
                ignore
        task = Task("tt", [py_open])
        cmd = CmdFactory(Strace, outstream=output)
        cmd.loader = self.loader_for_task(task)
        params = DefaultUpdate(dep_file=self.depfile_name, show_all=False,
                               keep_trace=False, backend='dbm',
                               check_file_uptodate='md5', codec_cls=JSONCodec)
        result = cmd.execute(params, ['tt'])
        self.assertEqual(0, result)

    def test_invalid_command_args(self):
        output = StringIO()
        cmd = CmdFactory(Strace, outstream=output)
        # fails if number of args != 1
        self.assertRaises(InvalidCommand, cmd.execute, {}, [])
        self.assertRaises(InvalidCommand, cmd.execute, {}, ['t1', 't2'])
