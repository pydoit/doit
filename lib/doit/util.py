"""Utility methods."""

import sys, types


def isgenerator(object):
    """Check if object type is a generator.

    @param object: object to test.
    @return: (bool) object is a generator?"""
    return type(object) is types.GeneratorType



class Debugger(object):
    """Make sure we can debug without all these stream redirection madness.

    To use it just call an instance.

    DEBUGGER()

    remember that you are one level below than where you put the statement.
    so the first thing you should do is go "up".

    after you finish bring it back to its previous configuration.

    DEBUGGER.done()
    """

    def __call__(self):
        """Start debugger."""
        self.out = sys.stdout
        self.err = sys.stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        # start pdb
        import pdb
        pdb.set_trace()

    def done(self):
        """Finish debugging. Restore std streams."""
        sys.stdout = self.out
        sys.stderr = self.err

#: A L{Debugger} instance
DEBUGGER = Debugger()




import hashlib
def md5sum(path):
    """Calculate the md5 sum from file content.

    @param path: (string) file path
    @return: (string) md5
    """
    f = open(path,'rb')
    result = hashlib.md5(f.read()).hexdigest()
    f.close()
    return result
