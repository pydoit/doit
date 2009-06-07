import os
import sys
import pdb
import StringIO

from doit import util


class TestIsGenerator(object):

    def testIsGeneratorYes(self):
        def giveme():
            for i in range(3):
                yield i
        g = giveme()
        assert util.isgenerator(g)
        for i in g: pass # just to get coverage on the givme function

    def testIsGeneratorNo(self):
        def giveme():
            return 5
        assert not util.isgenerator(giveme())




class TestDebugger(object):

    def setUp(self):
        def dumb_set_trace():pass
        self.original = pdb.set_trace
        pdb.set_trace = dumb_set_trace

    def tearDown(self):
        pdb.set_trace = self.original

    # starting the debugger makes stdout == __stdout__. same for stderr
    def testStart(self):
        sys.stdout = StringIO.StringIO()
        sys.stderr = StringIO.StringIO()
        util.DEBUGGER()
        assert sys.__stdout__ == sys.stdout
        assert sys.__stderr__ == sys.stderr

    # done restore stdout, stderr
    def testDone(self):
        out = sys.stdout = StringIO.StringIO()
        err = sys.stderr = StringIO.StringIO()
        util.DEBUGGER()
        util.DEBUGGER.done()
        assert out == sys.stdout
        assert err == sys.stderr




def test_md5():
    filePath = os.path.abspath(__file__+"/../sample_md5.txt")
    # result got using command line md5sum
    expected = "45d1503cb985898ab5bd8e58973007dd"
    assert expected == util.md5sum(filePath)

