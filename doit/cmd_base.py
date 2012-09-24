from .cmdparse import CmdParse


class Command(object):
    # doc attributes, should be sub-classed
    doc_purpose = ''
    doc_usage = ''
    doc_description = None # None value will completely ommit line from doc

    def __init__(self, options):
        self.name = self.__class__.__name__.lower()
        self.cmdparse = CmdParse(options)

    def parse_execute(self, in_args, **kwargs):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of self.execute
        """
        params, args = self.cmdparse.parse(in_args, **kwargs)
        return self.execute(params, args)

    def execute(self, params, args):
        raise NotImplementedError()


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
        if opt['short']:
            if opt['type'] is bool:
                opts_str.append('-%s' % opt['short'])
            else:
                opts_str.append('-%s ARG' % opt['short'])
        if opt['long']:
            if opt['type'] is bool:
                opts_str.append('--%s' % opt['long'])
            else:
                opts_str.append('--%s=ARG' % opt['long'])
        return ', '.join(opts_str)


    def help(self):
        """return help text"""
        text = []
        text.append("Purpose: %s" % self.doc_purpose)
        text.append("Usage:   doit %s %s" % (self.name, self.doc_usage))
        text.append('')

        text.append("Options:")
        for opt in self.cmdparse.options:
            # ignore option that cant be modified on cmd line
            if not (opt['short'] or opt['long']):
                continue

            opt_str = self._help_opt(opt)
            opt_help = opt['help'] % {'default':opt['default']}
            text.append(self._print_2_columns(opt_str, opt_help))
            # print bool inverse option
            if opt['inverse']:
                opt_str = '--%s' % opt['inverse']
                opt_help = 'opposite of --%s' % opt['long']
                text.append(self._print_2_columns(opt_str, opt_help))

        if self.doc_description is not None:
            text.append("")
            text.append("Description:")
            text.append(self.doc_description)
        return "\n".join(text)


