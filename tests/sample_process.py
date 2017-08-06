#! /usr/bin/env python3

# tests on CmdTask will use this script as an external process.
# - If you call this script with 3 or more arguments, the process returns
#   exit code (166).
# - If you call this script with arguments "please fail", it returns exit
#   code (11).
# - If you call this script with arguments "check env", it verifies the
#   existence of an environment variable called "GELKIPWDUZLOVSXE", with
#   value "1". If the variable is not found, the process returns exit code (99).
# - Otherwise, any first argument gets written to STDOUT. Any second argument
#   gets written to STDERR.

import os
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
    # check env
    if len(sys.argv) == 3 and sys.argv[1]=='check' and sys.argv[2]=='env':
        if os.environ.get('GELKIPWDUZLOVSXE') == '1':
            sys.exit(0)
        else:
            sys.exit(99)
    # ok
    if len(sys.argv) > 1:
        sys.stdout.write(sys.argv[1])
    if len(sys.argv) > 2:
        sys.stderr.write(sys.argv[2])
    sys.exit(0)
