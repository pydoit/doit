"""utility methods."""
import sys, types


def isgenerator(obj):
    """@return bool object is a generator?"""
    return type(obj) is types.GeneratorType




class Debug(object):
    """ make sure we can debug without all these stream redirection madness

    to use it just call an instance.

    DEBUGGER()

    remember that you are one level below than where you put the statement.
    so the first thing you should do is go "up".

    after you finish bring it back to its previous configuration.

    DEBUGGER.done()
    """
    def __call__(self):
        self.out = sys.stdout
        self.err = sys.stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        # start pdb
        import pdb;pdb.set_trace()

    def done(self):
        sys.stdout = self.out
        sys.stderr = self.err

DEBUGGER = Debug()




import hashlib
def md5sum(path):
    """@return string containing the md5 of the given file path."""
    f = open(path,'rb')
    result = hashlib.md5(f.read()).hexdigest()
    f.close()
    return result

# time signature from a file.
#import os
#signature = os.path.getmtime(path)
