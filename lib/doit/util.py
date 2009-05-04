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











############################################
# copied from http://twistedmatrix.com/trac/browser/tags/releases/twisted-8.0.0//twisted/python/util.py#L133

# Copyright (c) 2001-2008
# Allen Short
# Andrew Bennetts
# Apple Computer, Inc.
# Benjamin Bruheim
# Bob Ippolito
# Canonical Limited
# Christopher Armstrong
# David Reid
# Donovan Preston
# Eric Mangold
# Itamar Shtull-Trauring
# James Knight
# Jason A. Mobarak
# Jonathan Lange
# Jonathan D. Simms
# Jp Calderone
# J?rgen Hermann
# Kevin Turner
# Mary Gardiner
# Matthew Lefkowitz
# Massachusetts Institute of Technology
# Moshe Zadka
# Paul Swartz
# Pavel Pergamenshchik
# Ralph Meijer
# Sean Riley
# Travis B. Hartwell
# Thomas Herve
# Eyal Lotem
# Antoine Pitrou
# Andy Gayton

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from UserDict import UserDict

class OrderedDict(UserDict):
    """A UserDict that preserves insert order whenever possible."""
    def __init__(self, dict=None, **kwargs):
        self._order = []
        self.data = {}
        if dict is not None:
            if hasattr(dict,'keys'):
                self.update(dict)
            else:
                for k,v in dict: # sequence
                    self[k] = v
        if len(kwargs):
            self.update(kwargs)
    def __repr__(self):
        return '{'+', '.join([('%r: %r' % item) for item in self.items()])+'}'

    def __setitem__(self, key, value):
        if not self.has_key(key):
            self._order.append(key)
        UserDict.__setitem__(self, key, value)

    def copy(self):
        return self.__class__(self)

    def __delitem__(self, key):
        UserDict.__delitem__(self, key)
        self._order.remove(key)

    def iteritems(self):
        for item in self._order:
            yield (item, self[item])

    def items(self):
        return list(self.iteritems())

    def itervalues(self):
        for item in self._order:
            yield self[item]

    def values(self):
        return list(self.itervalues())

    def iterkeys(self):
        return iter(self._order)

    def keys(self):
        return list(self._order)

    def popitem(self):
        key = self._order[-1]
        value = self[key]
        del self[key]
        return (key, value)

    def setdefault(self, item, default):
        if self.has_key(item):
            return self[item]
        self[item] = default
        return default

    def update(self, d):
        for k, v in d.items():
            self[k] = v
