import inspect
import sys

import doit
from .cmdparse import CmdOption, CmdParse
from .exceptions import InvalidCommand, InvalidDodoFile
from .dependency import backend_map
from . import loader


def version_tuple(ver_in):
    """convert a version string or tuple into a 3-element tuple with ints
    Any part that is not a number (dev0, a2, b4) will be converted to -1
    """
    result = []
    parts = ver_in.split('.') if isinstance(ver_in, str) else ver_in
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

    def __init__(self):
        self.name = self.name or self.__class__.__name__.lower()
        Command.CMD_LIST.append(self.name)
        self.options = self.set_options()

    def set_options(self):
        """@reutrn list of CmdOption
        """
        opt_list = self.cmd_options
        return [CmdOption(opt) for opt in opt_list]


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
        params, args = CmdParse(self.options).parse(in_args)
        return self.execute(params, args)


    def help(self):
        """return help text"""
        text = []
        text.append("Purpose: %s" % self.doc_purpose)
        text.append("Usage:   doit %s %s" % (self.name, self.doc_usage))
        text.append('')

        text.append("Options:")
        for opt in self.options:
            text.extend(opt.help_doc())

        if self.doc_description is not None:
            text.append("")
            text.append("Description:")
            text.append(self.doc_description)
        return "\n".join(text)


######################################################################

# choose internal dependency file.
opt_depfile = {'name': 'dep_file',
               'short':'',
               'long': 'db-file',
               'type': str,
               'default': ".doit.db",
               'help': "file used to save successful runs"
               }

# dependency file DB backend
opt_backend = {
    'name': 'backend',
    'short':'',
    'long': 'backend',
    'type': str,
    'default': "dbm",
    'help': ("Select dependency file backend." +
             "Available options dbm, json, sqlite3. [default: %(default)s]")
}


#### options related to dodo.py
# select dodo file containing tasks
opt_dodo = {'name': 'dodoFile',
            'short':'f',
            'long': 'file',
            'type': str,
            'default': 'dodo.py',
            'help':"load task from dodo FILE [default: %(default)s]"
            }

# cwd
opt_cwd = {'name': 'cwdPath',
           'short':'d',
           'long': 'dir',
           'type': str,
           'default': None,
           'help':("set path to be used as cwd directory (file paths on " +
                   "dodo file are relative to dodo.py location.")
           }

# seek dodo file on parent folders
opt_seek_file = {'name': 'seek_file',
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
    def _load_from_module(module, cmd_list):
        """load task from a module or dict with module members"""
        if inspect.ismodule(module):
            members = dict(inspect.getmembers(module))
        else:
            members = module
        task_list = loader.load_tasks(members, cmd_list)
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
        return self._load_from_module(self.mod_dict, cmd.CMD_LIST)


class DodoTaskLoader(TaskLoader):
    """default task-loader create tasks from a dodo.py file"""
    cmd_options = (opt_dodo, opt_cwd, opt_seek_file)

    def load_tasks(self, cmd, params, args):
        dodo_module = loader.get_module(params['dodoFile'], params['cwdPath'],
                                        params['seek_file'])
        return self._load_from_module(dodo_module, cmd.CMD_LIST)



class DoitCmdBase(Command):
    """
    subclass must define:
    cmd_options => list of option dictionary (see CmdOption)
    _execute => method, argument names must be option names
    """
    base_options = (opt_depfile, opt_backend)

    def __init__(self, task_loader=None, dep_file=None, backend=None,
                 config=None, task_list=None, sel_tasks=None, outstream=None):
        """this initializer is usually just used on tests"""
        # FIXME 'or TaskLoader()' below is hack for tests
        self._loader = task_loader or TaskLoader()
        Command.__init__(self)
        # TODO: helper to test code should not be here
        self.dep_class = backend_map.get(backend)
        self.dep_file = dep_file   # (str) filename usually '.doit.db'
        self.config = config or {} # config from dodo.py & cmdline
        self.task_list = task_list # list of tasks
        self.sel_tasks = sel_tasks # from command line or default_tasks
        self.outstream = outstream or sys.stdout

    def set_options(self):
        """from base class - merge base_options, loader_options and cmd_options
        """
        opt_list = (self.base_options + self._loader.cmd_options +
                    self.cmd_options)
        return [CmdOption(opt) for opt in opt_list]

    def _execute(self): # pragma: no cover
        """to be subclassed - actual command implementation"""
        raise NotImplementedError

    def execute(self, params, args):
        """load dodo.py, set attributes and call self._execute"""
        self.task_list, self.config = self._loader.load_tasks(self, params,
                                                              args)
        self.sel_tasks = args or self.config.get('default_tasks')

        # check minversion
        minversion = self.config.get('minversion')
        if minversion:
            if version_tuple(minversion) > version_tuple(doit.__version__):
                msg = ('Please update doit. '
                'Minimum version required is {required}. '
                'You are using {actual}. ')
                raise InvalidDodoFile(msg.format(required=minversion,
                                                 actual=doit.__version__))

        # merge config values into params
        params.update_defaults(self.config)
        self.dep_file = params['dep_file']
        self.dep_class = backend_map.get(params['backend'])
        params['pos_args'] = args # hack
        params['continue_'] = params.get('continue') # hack

        # magic - create dict based on signature of _execute method
        args_name = inspect.getargspec(self._execute)[0]
        exec_params = dict((n, params[n]) for n in args_name if n!='self')
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
    to_process = set(sel_tasks) # str - task name
    # get initial task
    while to_process:
        task = tasks[to_process.pop()]
        processed.add(task.name)
        yield task
        # FIXME this does not take calc_dep into account
        for task_dep in task.task_dep + task.setup_tasks:
            if (task_dep not in processed) and (task_dep not in to_process):
                to_process.add(task_dep)
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
