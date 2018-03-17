import pytest

from doit.cmd_dumpdb import DumpDB

class TestCmdDumpDB(object):

    def testDefault(self, capsys, dep_manager):
        if dep_manager.whichdb in ('dbm', 'dbm.ndbm'): # pragma: no cover
            pytest.skip('%s not supported for this operation' % dep_manager.whichdb)
        # cmd_main(["help", "task"])
        dep_manager._set('tid', 'my_dep', 'xxx')
        dep_manager.close()
        cmd_dump = DumpDB()
        cmd_dump.execute({'dep_file': dep_manager.name}, [])
        out, err = capsys.readouterr()
        assert 'tid' in out
        assert 'my_dep' in out
        assert 'xxx' in out
