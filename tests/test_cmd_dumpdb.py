from dbm import whichdb

import pytest

from doit.cmd_dumpdb import DumpDB

class TestCmdDumpDB(object):

    def testDefault(self, capsys, dep_manager):
        # cmd_main(["help", "task"])
        dep_manager._set('tid', 'my_dep', 'xxx')
        dep_manager.close()
        dbm_kind = whichdb(dep_manager.name)
        if dbm_kind in ('dbm', 'dbm.ndbm'): # pragma: no cover
            pytest.skip(f'"{dbm_kind}" not supported for this operation')
        cmd_dump = DumpDB()
        cmd_dump.execute({'dep_file': dep_manager.name}, [])
        out, err = capsys.readouterr()
        assert 'tid' in out
        assert 'my_dep' in out
        assert 'xxx' in out
