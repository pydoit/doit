"""Parse command line options and execute it.

Built on top of getopt. optparse can't handle sub-commands.
"""
import getopt

class Command(object):
    """
    @ivar name (string): command name
    @ivar options (dict): command line options/arguments
       - name (string) : variable name
       - short (string): argument short name
       - long (string): argument long name
       - type (type): type of the variable. must be able to be initialized
                      taking a single string parameter.
                      if type is bool. option is just a flag. and if present
                      its value is set to True.
       - default (value from its type): default value
       - help (string): option description
    @ivar do_cmd (callable): function must have 2 parameters. it will be called
                             with the result of the parse method.
    @ivar doc (dict): dictionary containing help information. see _doc_fields.
    """
    # description can be None or string. other fields must be string.
    _doc_fields = ('purpose', 'usage', 'description')

    def __init__(self, name, options, do_cmd, doc):
        self.name = name
        self.options = options
        self.do_cmd = do_cmd
        self.doc = doc
        # sanity checks
        # doc dict must contain all fields.
        for field in self._doc_fields:
            assert field in self.doc
        # options must contain all fileds
        for opt in self.options:
            for field in ('name', 'short', 'long', 'type', 'default', 'help'):
                assert field in opt, "missing '%s' in %s" % (field, opt)

    def help(self):
        """return help text"""
        text = []
        text.append("Purpose: %s" % self.doc['purpose'])
        text.append("Usage:   doit %s %s" % (self.name, self.doc['usage']))
        text.append('')

        text.append("Options:")
        for opt in self.options:
            # ignore option that cant be modified on cmd line
            if not (opt['short'] or opt['long']):
                continue
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
            opt_help = opt['help'] % {'default':opt['default']}
            # arrange in 2 columns
            left = (', '.join(opts_str)).ljust(24)
            right = opt_help.replace('\n','\n'+ 28*' ')
            text.append("  %s  %s" % (left, right))

        if self.doc['description'] is not None:
            text.append("")
            text.append("Description:")
            text.append(self.doc['description'])
        return "\n".join(text)

    def get_short(self):
        """return string with short options for getopt"""
        short_list = ""
        for opt in self.options:
            if not opt['short']:
                continue
            short_list += opt['short']
            # ':' means option takes a value
            if opt['type'] is not bool:
                short_list += ':'
        return short_list

    def get_long(self):
        """return list with long options for getopt"""
        long_list = []
        for opt in self.options:
            long = opt['long']
            if not long:
                continue
            # '=' means option takes a value
            if opt['type'] is not bool:
                long += '='
            long_list.append(long)
        return long_list

    def get_option(self, opt_str):
        """return option dictionary from matching opt_str. or None"""
        for opt in self.options:
            if opt_str in ('-' + opt['short'], '--' + opt['long']):
                return opt

    def parse(self, in_args, **kwargs):
        """parse arguments into options(params) and positional arguments

        @param in_args (list - string): typically sys.argv[1:]
        @param kwargs: apart from options some "extra" values can be passed to
                       the command.
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             args (list - string): positional arguments
        """
        params = {}
        # add default values
        for opt in self.options:
            params[opt['name']] = opt.get('default', None)

        # global parameters (got from main command options)
        params.update(kwargs)

        # parse options using getopt
        opts,args = getopt.getopt(in_args,self.get_short(),self.get_long())

        # update params with values from command line
        for opt, val in opts:
            this = self.get_option(opt)
            if this['type'] is bool:
                params[this['name']] = True
            else:
                # FIXME check for errors
                params[this['name']] = this['type'](val)

        return params, args


    def __call__(self, in_args, **kwargs):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of do_cmd
        """
        params, args = self.parse(in_args, **kwargs)
        return self.do_cmd(params, args)
