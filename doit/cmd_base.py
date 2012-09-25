
from .cmdparse import CmdOption, CmdParse
from . import loader


class Command(object):
    """base command third-party should subclass this for commands that
    do no use tasks
    """
    # doc attributes, should be sub-classed
    doc_purpose = ''
    doc_usage = ''
    doc_description = None # None value will completely ommit line from doc

    # sequence of dicts
    cmd_options = tuple()

    def __init__(self):
        self.name = self.__class__.__name__.lower()
        self.options = self.set_options()

    def set_options(self):
        """@reutrn list of CmdOption
        """
        opt_list = self.cmd_options
        return [CmdOption(opt) for opt in opt_list]

    def execute(self, params, args):
        raise NotImplementedError()


    def parse_execute(self, in_args, **kwargs):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of self.execute
        """
        params, args = CmdParse(self.options).parse(in_args, **kwargs)
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



class DoitCmdBase(Command):
    base_options = (opt_dodo, opt_cwd, opt_seek_file, opt_depfile)

    def set_options(self):
        opt_list = self.base_options + self.cmd_options
        return [CmdOption(opt) for opt in opt_list]

    def read_dodo(self, params, args):
        # FIXME should get a tuple instead of dict
        dodo_tasks = loader.get_tasks(
            params['dodoFile'], params['cwdPath'], params['seek_file'],
            params['sub'].keys())
        self.task_list = dodo_tasks['task_list']
        self.config = dodo_tasks['config']
        params.update_defaults(self.config)
        self.sel_tasks = args or self.config.get('default_tasks')
        return params

