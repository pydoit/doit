#! /usr/bin/env python

# tests on CmdTask will use this script as an external process.
# 3 or more arguments. process return error exit (166)
# arguments "please fail". process return fail exit (11)
# first argument is sent to stdout
# second argument is sent to stderr

import sys

if __name__ == "__main__":
    # error
    if len(sys.argv) > 3:
        sys.exit(166)
    # fail
    if len(sys.argv) == 3 and sys.argv[1]=='please' and sys.argv[2]=='fail':
        sys.stdout.write("out ouch")
        sys.stderr.write("err output on failure")
        sys.exit(11)
    # ok
    if len(sys.argv) > 1:
        sys.stdout.write(sys.argv[1])
    if len(sys.argv) > 2:
        sys.stderr.write(sys.argv[2])
    sys.exit(0)
