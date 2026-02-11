import io
import unittest
import contextlib
from dbm import whichdb

from doit.cmd_dumpdb import DumpDB
from tests.support import DepManagerMixin


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
