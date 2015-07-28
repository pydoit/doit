'''This module is work-around the bug http://bugs.python.org/issue10845

This bug only affects python2.7 multiprocessing  on Windows.
It gets confused with module named __main__.py, so use this module instead
of `__main__.py` as an entry point.
'''

import sys # pragma: no cover

def main(): # pragma: no cover
    from doit.doit_cmd import DoitMain
    sys.exit(DoitMain().run(sys.argv[1:]))

