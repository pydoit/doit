
#! /usr/bin/env python

import sys

from doit.cmd_base import Command
from doit.doit_cmd import DoitMain


class MyCmd(Command):
    doc_purpose = 'test extending doit commands'
    doc_usage = '[XXX]'
    doc_description = 'my command description'

    def execute(self, opt_values, pos_args):
        print "this command does nothing!"


class MyTool(DoitMain):
    def get_commands(self):
        cmds = DoitMain.get_commands(self)
        my_cmd = MyCmd()
        cmds[my_cmd.name] = my_cmd
        return cmds


if __name__ == "__main__":
    sys.exit(MyTool().run(sys.argv[1:]))

