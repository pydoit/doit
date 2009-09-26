#! /usr/bin/env python

# tests on CmdTask will use this script as an external process.
# just print out all arguments

import sys

if __name__ == "__main__":
    print " ".join(sys.argv[1:])
    sys.exit(0)
