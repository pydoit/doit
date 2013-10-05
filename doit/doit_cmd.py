"""doit CLI (command line interface)"""

import os
import sys
import traceback
import six

import doit
from .exceptions import InvalidDodoFile, InvalidCommand, InvalidTask
from .cmdparse import CmdParseError
from .cmd_base import DodoTaskLoader, DoitCmdBase
from .cmd_help import Help
from .cmd_run import Run
from .cmd_clean import Clean
from .cmd_list import List
from .cmd_forget import Forget
from .cmd_ignore import Ignore
from .cmd_auto import Auto
from .cmd_dumpdb import DumpDB
from .cmd_strace import Strace
from .cmd_completion import TabCompletion


class DoitMain(object):
    DOIT_CMDS = (Help, Run, List, Clean, Forget, Ignore, Auto, DumpDB,
                 Strace, TabCompletion)
    TASK_LOADER = DodoTaskLoader

    def __init__(self, task_loader=None):
        self.task_loader = task_loader if task_loader else self.TASK_LOADER()
        self.sub_cmds = {} # dict with available sub-commands

    @staticmethod
    def print_version():
        """print doit version (includes path location)"""
        six.print_(".".join([str(i) for i in doit.__version__]))
        six.print_("bin @", os.path.abspath(__file__))
        six.print_("lib @", os.path.dirname(os.path.abspath(doit.__file__)))


    def get_commands(self):
        """get all sub-commands"""
        sub_cmds = {}
        # core doit commands
        for cmd_cls in (self.DOIT_CMDS):
            if issubclass(cmd_cls, DoitCmdBase):
                cmd = cmd_cls(task_loader=self.task_loader)
                cmd.doit_app = self # hack used by Help/TabComplete command
            else:
                cmd = cmd_cls()
            sub_cmds[cmd.name] = cmd
        return sub_cmds


    def process_args(self, cmd_args):
        """process cmd line set "global" variables/parameters
        return list of args without processed variables
        """
        # get cmdline variables from args
        doit.reset_vars()
        args_no_vars = []
        for arg in cmd_args:
            if (arg[0] != '-') and ('=' in arg):
                name, value = arg.split('=', 1)
                doit.set_var(name, value)
            else:
                args_no_vars.append(arg)
        return args_no_vars


    def run(self, cmd_args):
        """entry point for all commands

        return codes:
          0: tasks executed successfully
          1: one or more tasks failed
          2: error while executing a task
          3: error before task execution starts,
             in this case the Reporter is not used.
             So be aware if you expect a different formatting (like JSON)
             from the Reporter.
        """
        self.sub_cmds = self.get_commands()

        # special parameters that dont run anything
        if cmd_args:
            if cmd_args[0] == "--version":
                self.print_version()
                return 0
            if cmd_args[0] == "--help":
                Help.print_usage(self.sub_cmds)
                return 0

        # get "global vars" from cmd-line
        args = self.process_args(cmd_args)

        # get specified sub-command or use default='run'
        if len(args) == 0 or args[0] not in list(six.iterkeys(self.sub_cmds)):
            command = 'run'
        else:
            command = args.pop(0)

        # execute command
        try:
            return self.sub_cmds[command].parse_execute(args)

        # dont show traceback for user errors.
        except (CmdParseError, InvalidDodoFile,
                InvalidCommand, InvalidTask) as err:
            sys.stderr.write("ERROR: %s\n" % str(err))
            return 3

        except Exception:
            sys.stderr.write(traceback.format_exc())
            return 3
