import pytest

from doit.cmd_dumpdb import DumpDB

class TestCmdDumpDB(object):

    def testDefault(self, capsys, depfile):
        if depfile.whichdb in ('dbm', 'dbm.ndbm'): # pragma: no cover
            pytest.skip('%s not supported for this operation' % depfile.whichdb)
        # cmd_main(["help", "task"])
        depfile._set('tid', 'my_dep', 'xxx')
        depfile.close()
        cmd_dump = DumpDB()
        cmd_dump.execute({'dep_file': depfile.name}, [])
        out, err = capsys.readouterr()
        assert 'tid' in out
        assert 'my_dep' in out
        assert 'xxx' in out
