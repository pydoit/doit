"""doit CLI (command line interface)"""

import os
import sys
import itertools
import traceback
import importlib
from collections import defaultdict
import six
from six.moves import configparser

from .version import VERSION
from .exceptions import InvalidDodoFile, InvalidCommand, InvalidTask
from .cmdparse import CmdParseError
from .cmd_base import DodoTaskLoader, DoitCmdBase
from .cmd_help import Help
from .cmd_run import Run
from .cmd_clean import Clean
from .cmd_list import List
from .cmd_info import Info
from .cmd_forget import Forget
from .cmd_ignore import Ignore
from .cmd_auto import Auto
from .cmd_dumpdb import DumpDB
from .cmd_strace import Strace
from .cmd_completion import TabCompletion
from .cmd_resetdep import ResetDep


# used to save variable values passed from command line
_CMDLINE_VARS = None

def reset_vars():
    global _CMDLINE_VARS
    _CMDLINE_VARS = {}

def get_var(name, default=None):
    return _CMDLINE_VARS.get(name, default)

def set_var(name, value):
    _CMDLINE_VARS[name] = value



class PluginRegistry(object):
    """simple plugin system to load code dynamically

    Plugins must be explicitly loaded (no scanning of files and folders is done
    to find plugins).

    There is no requirements of interface or checking of loaded plugins (that's
    up to application code if desirable). The registry is responsible only for
    loading a piece of code and keeping a reference to it.
    """
    def __init__(self):
        self._plugins = defaultdict(list) # category: value

    def __getitem__(self, key):
        """get all plugins from a given category"""
        return self._plugins[key]

    def add(self, category, module_name, obj_name):
        """get reference to obj from named module/obj"""
        module = importlib.import_module(module_name)
        self._plugins[category].append(getattr(module, obj_name))



class DoitMain(object):
    DOIT_CMDS = (Help, Run, List, Info, Clean, Forget, Ignore, Auto, DumpDB,
                 Strace, TabCompletion, ResetDep)
    TASK_LOADER = DodoTaskLoader

    def __init__(self, task_loader=None, config_filenames='doit.cfg'):
        self.task_loader = task_loader if task_loader else self.TASK_LOADER()
        self.sub_cmds = {} # dict with available sub-commands
        self.plugins = PluginRegistry()
        self.config = configparser.SafeConfigParser(allow_no_value=True)
        self.config.optionxform = str  # preserve case of option names
        self.load_config_ini(config_filenames)


    def load_config_ini(self, filenames):
        """read config from INI files

        :param files: str or list of str.
                      Like ConfigParser.read() param filenames
        """
        self.config.read(filenames)

        if self.config.has_section('command'):
            for name, _ in self.config.items('command'):
                obj_name, mod_name = name.split('@')
                self.plugins.add('command', mod_name, obj_name)


    @staticmethod
    def print_version():
        """print doit version (includes path location)"""
        six.print_(".".join([str(i) for i in VERSION]))
        six.print_("lib @", os.path.dirname(os.path.abspath(__file__)))


    def get_commands(self):
        """get all sub-commands"""
        sub_cmds = {}
        # core doit commands
        for cmd_cls in itertools.chain(self.DOIT_CMDS, self.plugins['command']):
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
        reset_vars()
        args_no_vars = []
        for arg in cmd_args:
            if (arg[0] != '-') and ('=' in arg):
                name, value = arg.split('=', 1)
                set_var(name, value)
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
            cmd_name = 'run'
        else:
            cmd_name = args.pop(0)
        command = self.sub_cmds[cmd_name]

        # execute command
        try:
            return command.parse_execute(args)

        # dont show traceback for user errors.
        except (CmdParseError, InvalidDodoFile,
                InvalidCommand, InvalidTask) as err:
            sys.stderr.write("ERROR: %s\n" % str(err))
            return 3

        except Exception:
            if command.pdb: # pragma: no cover
                import pdb
                pdb.post_mortem(sys.exc_info()[2])
            sys.stderr.write(traceback.format_exc())
            return 3
