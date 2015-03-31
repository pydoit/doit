import inspect
import sys
from collections import deque

import six

from . import version
from .cmdparse import CmdOption, CmdParse
from .exceptions import InvalidCommand, InvalidDodoFile
from .dependency import backend_map, CHECKERS
from . import loader


def version_tuple(ver_in):
    """convert a version string or tuple into a 3-element tuple with ints
    Any part that is not a number (dev0, a2, b4) will be converted to -1
    """
    result = []
    if isinstance(ver_in, six.string_types):
        parts = ver_in.split('.')
    else:
        parts = ver_in
    for rev in parts:
        try:
            result.append(int(rev))
        except:
            result.append(-1)
    assert len(result) == 3
    return result


class Command(object):
    """third-party should subclass this for commands that do no use tasks

    :cvar name: (str) name of sub-cmd to be use from cmdline
    :cvar doc_purpose: (str) single line cmd description
    :cvar doc_usage: (str) describe accepted parameters
    :cvar doc_description: (str) long description/help for cmd
    :cvar cmd_options:
          (list of dict) see cmdparse.CmdOption for dict format
    """
    CMD_LIST = [] # register with the name of all created commands

    # if not specified uses the class name
    name = None

    # doc attributes, should be sub-classed
    doc_purpose = ''
    doc_usage = ''
    doc_description = None # None value will completely ommit line from doc

    # sequence of dicts
    cmd_options = tuple()

    # `execute_tasks` indicates wheather this command execute task's actions.
    # This is used by the loader to indicate when delayed task creation
    # should be used.
    execute_tasks = False

    def __init__(self):
        self.name = self.get_name()
        Command.CMD_LIST.append(self.name)
        self.options = self.set_options()
        self.config_vals = {}
        # Use post-mortem PDB in case of error loading tasks.
        # Only available for `run` command.
        self.pdb = False

    @classmethod
    def get_name(cls):
        """get command name as used from command line"""
        return cls.name or cls.__name__.lower()

    def set_options(self):
        """@reutrn list of CmdOption
        """
        opt_list = self.cmd_options
        return [CmdOption(opt) for opt in opt_list]


    def configure(self, vals):
        """update config_vals

        :param vals: dict

        Set extra configuration values, this vals can come from:
         * directly passed when using the API - through DoitMain.run()
         * from an INI configuration file
        """
        self.config_vals.update(vals)


    def execute(self, opt_values, pos_args): # pragma: no cover
        """execute command
        :param opt_values: (dict) with cmd_options values
        :param pos_args: (list) of cmd-line positinal arguments
        """
        raise NotImplementedError()


    def parse_execute(self, in_args):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of self.execute
        """
        cmdparse = CmdParse(self.options)
        cmdparse.overwrite_defaults(self.config_vals)
        params, args = cmdparse.parse(in_args)
        self.pdb = params.get('pdb', False)
        return self.execute(params, args)


    def help(self):
        """return help text"""
        cmdparse = CmdParse(self.options)
        cmdparse.overwrite_defaults(self.config_vals)

        text = []
        text.append("Purpose: %s" % self.doc_purpose)
        text.append("Usage:   doit %s %s" % (self.name, self.doc_usage))
        text.append('')

        text.append("Options:")
        for opt in cmdparse.options:
            text.extend(opt.help_doc())

        if self.doc_description is not None:
            text.append("")
            text.append("Description:")
            text.append(self.doc_description)
        return "\n".join(text)


######################################################################

# choose internal dependency file.
opt_depfile = {
    'name': 'dep_file',
    'short':'',
    'long': 'db-file',
    'type': str,
    'default': ".doit.db",
    'help': "file used to save successful runs [default: %(default)s]"
}

# dependency file DB backend
opt_backend = {
    'name': 'backend',
    'short':'',
    'long': 'backend',
    'type': str,
    'default': "dbm",
    'help': ("Select dependency file backend. " +
             "Available options dbm, json, sqlite3. [default: %(default)s]")
}

opt_check_file_uptodate = {
    'name': 'check_file_uptodate',
    'short': '',
    'long': 'check_file_uptodate',
    'type': str,
    'default': 'md5',
    'help': """\
Choose how to check if files have been modified.
Available options [default: %(default)s]:
  'md5': use the md5sum
  'timestamp': use the timestamp
"""
}



#### options related to dodo.py
# select dodo file containing tasks
opt_dodo = {
    'name': 'dodoFile',
    'short':'f',
    'long': 'file',
    'type': str,
    'default': 'dodo.py',
    'help':"load task from dodo FILE [default: %(default)s]"
}

# cwd
opt_cwd = {
    'name': 'cwdPath',
    'short':'d',
    'long': 'dir',
    'type': str,
    'default': None,
    'help':("set path to be used as cwd directory (file paths on " +
            "dodo file are relative to dodo.py location).")
}

# seek dodo file on parent folders
opt_seek_file = {
    'name': 'seek_file',
    'short': 'k',
    'long': 'seek-file',
    'type': bool,
    'default': False,
    'help': ("seek dodo file on parent folders " +
             "[default: %(default)s]")
}


class TaskLoader(object):
    """task-loader interface responsible of creating Task objects

    Subclasses must implement the method `load_tasks`

    :cvar cmd_options:
          (list of dict) see cmdparse.CmdOption for dict format
    """
    cmd_options = ()

    def load_tasks(self, cmd, opt_values, pos_args): # pragma: no cover
        """load tasks and DOIT_CONFIG

        :return: (tuple) list of Task, dict with DOIT_CONFIG options
        :param cmd: (doit.cmd_base.Command) current command being executed
        :param opt_values: (dict) with values for cmd_options
        :param pos_args: (list str) positional arguments from command line
        """
        raise NotImplementedError()

    @staticmethod
    def _load_from(cmd, namespace, cmd_list):
        """load task from a module or dict with module members"""
        if inspect.ismodule(namespace):
            members = dict(inspect.getmembers(namespace))
        else:
            members = namespace
        task_list = loader.load_tasks(members, cmd_list, cmd.execute_tasks)
        doit_config = loader.load_doit_config(members)
        return task_list, doit_config


class ModuleTaskLoader(TaskLoader):
    """load tasks from a module/dictionary containing task generators
    Usage: `ModuleTaskLoader(my_module)` or `ModuleTaskLoader(globals())`
    """
    cmd_options = ()

    def __init__(self, mod_dict):
        self.mod_dict = mod_dict

    def load_tasks(self, cmd, params, args):
        return self._load_from(cmd, self.mod_dict, cmd.CMD_LIST)


class DodoTaskLoader(TaskLoader):
    """default task-loader create tasks from a dodo.py file"""
    cmd_options = (opt_dodo, opt_cwd, opt_seek_file)

    def load_tasks(self, cmd, params, args):
        dodo_module = loader.get_module(params['dodoFile'], params['cwdPath'],
                                        params['seek_file'])
        return self._load_from(cmd, dodo_module, cmd.CMD_LIST)



class DoitCmdBase(Command):
    """
    subclass must define:
    cmd_options => list of option dictionary (see CmdOption)
    _execute => method, argument names must be option names
    """
    base_options = (opt_depfile, opt_backend, opt_check_file_uptodate)

    def __init__(self, task_loader):
        """this initializer is usually just used on tests"""
        self._loader = task_loader
        Command.__init__(self)
        self.sel_tasks = None # selected tasks for command
        self.dep_manager = None #
        self.outstream = sys.stdout

    def set_options(self):
        """from base class - merge base_options, loader_options and cmd_options
        """
        opt_list = (self.base_options + self._loader.cmd_options +
                    self.cmd_options)
        return [CmdOption(opt) for opt in opt_list]

    def _execute(self): # pragma: no cover
        """to be subclassed - actual command implementation"""
        raise NotImplementedError


    @staticmethod
    def check_minversion(minversion):
        """check if this version of doit statify minimum required version
        Minimum version specified by configuration on dodo.
        """
        if minversion:
            if version_tuple(minversion) > version_tuple(version.VERSION):
                msg = ('Please update doit. '
                       'Minimum version required is {required}. '
                       'You are using {actual}. ')
                raise InvalidDodoFile(msg.format(required=minversion,
                                                 actual=version.VERSION))

    @staticmethod
    def get_checker_cls(check_file_uptodate):
        """return checker class to be used by dep_manager"""
        if isinstance(check_file_uptodate, six.string_types):
            if check_file_uptodate not in CHECKERS:
                msg = ("No check_file_uptodate named '{}'."
                       " Type 'doit help run' to see a list "
                       "of available checkers.")
                raise InvalidCommand(msg.format(check_file_uptodate))
            return CHECKERS[check_file_uptodate]
        else:
            # user defined class
            return check_file_uptodate


    def execute(self, params, args):
        """load dodo.py, set attributes and call self._execute

        :param params: instance of cmdparse.DefaultUpdate
        :param args: list of string arguments (containing task names)
        """
        self.task_list, dodo_config = self._loader.load_tasks(self, params,
                                                              args)
        # merge config values from dodo.py into params
        params.update_defaults(dodo_config)

        self.check_minversion(params.get('minversion'))

        # set selected tasks for command
        self.sel_tasks = args or params.get('default_tasks')

        # create dep manager
        dep_class = backend_map.get(params['backend'])
        checker_cls = self.get_checker_cls(params['check_file_uptodate'])
        # note the command have the responsability to call dep_manager.close()
        self.dep_manager = dep_class(params['dep_file'], checker_cls)

        # hack to pass parameter into _execute() calls that are not part
        # of command line options
        params['pos_args'] = args
        params['continue_'] = params.get('continue')

        # magic - create dict based on signature of _execute() method.
        # this done so that _execute() have a nice API with name parameters
        # instead of just taking a dict.
        args_name = inspect.getargspec(self._execute)[0]
        exec_params = dict((n, params[n]) for n in args_name if n != 'self')
        return self._execute(**exec_params)


# helper functions to find list of tasks


def check_tasks_exist(tasks, name_list):
    """check task exist"""
    if not name_list:
        return
    for task_name in name_list:
        if task_name not in tasks:
            msg = "'%s' is not a task."
            raise InvalidCommand(msg % task_name)


# this is used by commands that do not execute tasks (list, clean, forget...)
def tasks_and_deps_iter(tasks, sel_tasks, yield_duplicates=False):
    """iterator of select_tasks and its dependencies
    @param tasks (dict - Task)
    @param sel_tasks(list - str)
    """
    processed = set() # str - task name
    to_process = deque(sel_tasks) # str - task name
    # get initial task
    while to_process:
        task = tasks[to_process.popleft()]
        processed.add(task.name)
        yield task
        # FIXME this does not take calc_dep into account
        for task_dep in task.task_dep + task.setup_tasks:
            if (task_dep not in processed) and (task_dep not in to_process):
                to_process.append(task_dep)
            elif yield_duplicates:
                yield tasks[task_dep]


def subtasks_iter(tasks, task):
    """find all subtasks for a given task
    @param tasks (dict - Task)
    @param task (Task)
    """
    for name in task.task_dep:
        dep = tasks[name]
        if dep.is_subtask:
            yield dep
