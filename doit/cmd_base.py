import inspect
import sys

from .cmdparse import CmdOption, CmdParse
from . import loader


class Command(object):
    """base command third-party should subclass this for commands that
    do no use tasks
    """
    CMD_LIST = [] # register with the name of all created commands

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
        @var opt_values: (dict) with cmd_options values
        @var pos_args: (list) of cmd-line positinal arguments
        """
        raise NotImplementedError()


    def parse_execute(self, in_args):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of self.execute
        """
        params, args = CmdParse(self.options).parse(in_args)
        return self.execute(params, args)


    @staticmethod
    def _print_2_columns(col1, col2):
        """print using a 2-columns format """
        column1_len = 24
        column2_start = 28
        left = (col1).ljust(column1_len)
        right = col2.replace('\n', '\n'+ column2_start * ' ')
        return "  %s  %s" % (left, right)


    def _help_opt(self, opt):
        """return string of option's short and long name
        i.e.:   -f ARG, --file=ARG
        @param opt: (dict) see self.options
        """
        opts_str = []
        if opt.short:
            if opt.type is bool:
                opts_str.append('-%s' % opt.short)
            else:
                opts_str.append('-%s ARG' % opt.short)
        if opt.long:
            if opt.type is bool:
                opts_str.append('--%s' % opt.long)
            else:
                opts_str.append('--%s=ARG' % opt.long)
        return ', '.join(opts_str)


    def help(self):
        """return help text"""
        text = []
        text.append("Purpose: %s" % self.doc_purpose)
        text.append("Usage:   doit %s %s" % (self.name, self.doc_usage))
        text.append('')

        text.append("Options:")
        for opt in self.options:
            # ignore option that cant be modified on cmd line
            if not (opt.short or opt.long):
                continue

            opt_str = self._help_opt(opt)
            opt_help = opt.help % {'default': opt.default}
            text.append(self._print_2_columns(opt_str, opt_help))
            # print bool inverse option
            if opt.inverse:
                opt_str = '--%s' % opt.inverse
                opt_help = 'opposite of --%s' % opt.long
                text.append(self._print_2_columns(opt_str, opt_help))

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
                 'short': '',
                 'long': 'seek-file',
                 'type': bool,
                 'default': False,
                 'help': ("seek dodo file on parent folders " +
                          "[default: %(default)s]")
                 }


class TaskLoader(object):
    """task-loader interface responsible of creating Task objects

    Subclasses must implement the method `load_tasks`

    @cvar cmd_options (list of dict) see cmdparse.CmdOption for dict format
    """
    cmd_options = ()

    def load_tasks(self, cmd, opt_values, pos_args): # pragma: no cover
        """load tasks and DOIT_CONFIG
        @return (tuple) list of Task, dict with DOIT_CONFIG options
        @param cmd (cmd_base.Command) current command being executed
        @param opt_values (dict) with values for cmd_options
        @para pos_args (list str) positional arguments from command line
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
    base_options = (opt_depfile,)

    def __init__(self, task_loader=None, dep_file=None, config=None,
                 task_list=None, sel_tasks=None, outstream=None):
        """this initializer is usually just used on tests"""
        self._loader = task_loader or TaskLoader()
        Command.__init__(self)
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

        # merge config values into params
        params.update_defaults(self.config)
        self.dep_file = params['dep_file']
        params['pos_args'] = args # hack
        params['continue_'] = params.get('continue') # hack
        self.sel_tasks = args or self.config.get('default_tasks')

        # magic - create dict based on signature of _execute method
        args_name = inspect.getargspec(self._execute)[0]
        exec_params = dict((n, params[n]) for n in args_name if n!='self')
        return self._execute(**exec_params)



