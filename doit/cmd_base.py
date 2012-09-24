from .cmdparse import CmdOption, CmdParse


class Command(object):
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


