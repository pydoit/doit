import inspect
import sys

from .cmdparse import CmdOption, CmdParse
from . import loader


class Command(object):
    """base command third-party should subclass this for commands that
    do no use tasks
    """
    CMD_LIST = [] # register with the name of all created commands

    # doc attributes, should be sub-classed
    doc_purpose = ''
    doc_usage = ''
    doc_description = None # None value will completely ommit line from doc

    # sequence of dicts
    cmd_options = tuple()

    def __init__(self):
        self.name = self.__class__.__name__.lower()
        Command.CMD_LIST.append(self.name)
        self.options = self.set_options()

    def set_options(self):
        """@reutrn list of CmdOption
        """
        opt_list = self.cmd_options
        return [CmdOption(opt) for opt in opt_list]


    def execute(self, params, args): # pragma: no cover
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
    cmd_options = ()
    def load_tasks(self, cmd, params, args):
        pass


class DodoTaskLoader(TaskLoader):
    cmd_options = (opt_dodo, opt_cwd, opt_seek_file)

    @staticmethod
    def load_tasks(cmd, params, args):
        dodo_tasks = loader.get_tasks(
            params['dodoFile'], params['cwdPath'], params['seek_file'],
            cmd.CMD_LIST)
        cmd.task_list = dodo_tasks['task_list']
        params.update_defaults(dodo_tasks['config'])
        cmd.config = params.copy()
        cmd.config['pos_args'] = args # hack
        cmd.sel_tasks = args or cmd.config.get('default_tasks')
        cmd.dep_file = cmd.config['dep_file']



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
        opt_list = (self.base_options + self._loader.cmd_options +
                    self.cmd_options)
        return [CmdOption(opt) for opt in opt_list]

    def _execute(self): # pragma: no cover
        raise NotImplementedError

    def execute(self, params, args):
        self._loader.load_tasks(self, params, args)
        args_name = inspect.getargspec(self._execute)[0]
        exec_params = dict((n, self.config[n]) for n in args_name if n!='self')
        return self._execute(**exec_params)



