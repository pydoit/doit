import io
import os
import shutil
import tempfile
import unittest
import contextlib
from dbm import whichdb

from doit.cmd_base import DodoTaskLoader, ModuleTaskLoader
from doit.cmdparse import DefaultUpdate
from doit.cmd_dumpdb import DumpDB
from tests.support import DepManagerMixin, RestoreCwdMixin


class TestCmdDumpDB(DepManagerMixin, unittest.TestCase):

    def testDefault(self):
        # cmd_main(["help", "task"])
        self.dep_manager._set('tid', 'my_dep', 'xxx')
        self.dep_manager.close()
        dbm_kind = whichdb(self.dep_manager.name)
        if dbm_kind in ('dbm', 'dbm.ndbm'):  # pragma: no cover
            self.skipTest(f'"{dbm_kind}" not supported for this operation')
        cmd_dump = DumpDB()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cmd_dump.execute({'dep_file': self.dep_manager.name}, [])
        got = out.getvalue()
        self.assertIn('tid', got)
        self.assertIn('my_dep', got)
        self.assertIn('xxx', got)


class TestCmdDumpDBDodoConfig(DepManagerMixin, RestoreCwdMixin,
                              unittest.TestCase):
    """dumpdb takes dep_file from DOIT_CONFIG (issue #126)"""

    def setUp(self):
        super().setUp()
        self.dep_manager._set('tid', 'my_dep', 'xxx')
        self.dep_manager.close()
        dbm_kind = whichdb(self.dep_manager.name)
        if dbm_kind in ('dbm', 'dbm.ndbm'):  # pragma: no cover
            self.skipTest(f'"{dbm_kind}" not supported for this operation')

    def dump(self, cmd_dump, opt_values):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cmd_dump.execute(opt_values, [])
        return out.getvalue()

    def test_dep_file_from_module_config(self):
        # API usage: DOIT_CONFIG is taken from the loader namespace
        loader = ModuleTaskLoader(
            {'DOIT_CONFIG': {'dep_file': self.dep_manager.name}})
        cmd_dump = DumpDB(task_loader=loader)
        opt_values = DefaultUpdate()
        opt_values.set_default('dep_file', '.doit.db')
        got = self.dump(cmd_dump, opt_values)
        self.assertIn('tid', got)
        self.assertIn('my_dep', got)
        self.assertIn('xxx', got)

    def test_dep_file_from_dodo_file(self):
        # CLI usage: DOIT_CONFIG is taken from the dodo file
        tmpdir = tempfile.mkdtemp(prefix='doit-test-dumpdb-')
        self.addCleanup(shutil.rmtree, tmpdir, True)
        dodo_name = os.path.join(tmpdir, 'dumpdb_sample.py')
        with open(dodo_name, 'w') as fp:
            fp.write("DOIT_CONFIG = {'dep_file': %r}\n" %
                     self.dep_manager.name)
        loader = DodoTaskLoader()
        cmd_dump = DumpDB(task_loader=loader)
        opt_values = DefaultUpdate()
        opt_values.set_default('dep_file', '.doit.db')
        opt_values['dodoFile'] = dodo_name
        got = self.dump(cmd_dump, opt_values)
        self.assertIn('tid', got)
        self.assertIn('my_dep', got)
        self.assertIn('xxx', got)

    def test_dep_file_cmdline_takes_precedence(self):
        # a dep_file set from the command line is not
        # overwritten by the value from DOIT_CONFIG
        loader = ModuleTaskLoader(
            {'DOIT_CONFIG': {'dep_file': 'no_such_file.db'}})
        cmd_dump = DumpDB(task_loader=loader)
        opt_values = DefaultUpdate()
        opt_values['dep_file'] = self.dep_manager.name
        got = self.dump(cmd_dump, opt_values)
        self.assertIn('tid', got)
        self.assertIn('my_dep', got)
        self.assertIn('xxx', got)

    def test_no_dodo_file(self):
        # dumpdb must work when there is no dodo file at all
        loader = DodoTaskLoader()
        cmd_dump = DumpDB(task_loader=loader)
        opt_values = DefaultUpdate()
        opt_values['dep_file'] = self.dep_manager.name
        opt_values['dodoFile'] = 'no_such_dodo_file.py'
        got = self.dump(cmd_dump, opt_values)
        self.assertIn('tid', got)
        self.assertIn('my_dep', got)
        self.assertIn('xxx', got)
