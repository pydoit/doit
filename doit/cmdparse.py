"""Parse command line options and execute it.

Built on top of getopt. optparse can't handle sub-commands.
"""
import getopt


class DefaultUpdate(dict):
    """A dictionary with support that has an "update_defaults" method where
    only items with default values are updated. A default value is added with
    the method "set_default".
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        # set of keys that have a non-default value
        self._non_default_keys = set()

    def set_default(self, key, value):
        """set default value for given key"""
        dict.__setitem__(self, key, value)

    def update_defaults(self, update_dict):
        """do not update items that already have a non-default value"""
        for key, value in update_dict.iteritems():
            if key in self._non_default_keys:
                continue
            self[key] = value

    def __setitem__(self, key, value):
        try:
            self._non_default_keys.add(key)
        # http://bugs.python.org/issue826897
        except AttributeError:
            self._non_default_keys = set()
            self._non_default_keys.add(key)
        dict.__setitem__(self, key, value)

    # http://bugs.python.org/issue826897
    def __setstate__(self, adict):
        pass

class CmdParseError(Exception):
    """Error parsing options """


class Command(object):
    """Process string with command options

    @ivar name (string): command name
    @ivar options (dict): command line options/arguments
       - name (string) : variable name
       - short (string): argument short name
       - long (string): argument long name
       - inverse (string): argument long name to be the inverse of the default
                           value (only used by boolean options)
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
    _type = "Command option"
    # description can be None or string. other fields must be string.
    _doc_fields = ('purpose', 'usage', 'description')
    _option_fields = ('name', 'short', 'long', 'inverse',
                      'type', 'default', 'help')
    # default values for option meta data
    _defaults = {'short': '',
                 'long': '',
                 'inverse': '',
                 'type': str,
                 'help': ''}


    def __init__(self, name, options, do_cmd, doc):
        self.name = name
        self.do_cmd = do_cmd
        self.options = []

        for original_opt in options:
            opt = dict(original_opt)

            # options must contain these fields
            for field in ('name', 'default',):
                if field not in opt:
                    msg = "%s dict from '%s' missing required property '%s'"
                    raise CmdParseError(msg % (self._type, self.name, field))

            # options can not contain any unrecognized field
            for field in opt.keys():
                if field not in self._option_fields:
                    msg = "%s dict from '%s' contains invalid property '%s'"
                    raise CmdParseError(msg % (self._type, self.name, field))

            # add defaults
            for key, value in self._defaults.iteritems():
                if key not in opt:
                    opt[key] = value
            self.options.append(opt)

        # doc must be None or dict contain all fields.
        if doc is not None:
            self.doc = dict(doc)
            for field in self._doc_fields:
                assert field in self.doc
        else:
            self.doc = None

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
        assert self.doc is not None
        text = []
        text.append("Purpose: %s" % self.doc['purpose'])
        text.append("Usage:   doit %s %s" % (self.name, self.doc['usage']))
        text.append('')

        text.append("Options:")
        for opt in self.options:
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
            long_name = opt['long']
            if not long_name:
                continue
            # '=' means option takes a value
            if opt['type'] is not bool:
                long_name += '='
            long_list.append(long_name)
            if opt['inverse']:
                long_list.append(opt['inverse'])
        return long_list

    def get_option(self, opt_str):
        """return tuple
            - option dictionary from matching opt_str. or None
            - (bool) matched inverse
        """
        for opt in self.options:
            if opt_str in ('-' + opt['short'], '--' + opt['long']):
                return opt, False
            if opt_str == '--' + opt['inverse']:
                return opt, True
        return None, None

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
        params = DefaultUpdate()
        # add default values
        for opt in self.options:
            params.set_default(opt['name'], opt.get('default', None))

        # global parameters (got from main command options)
        params.update(kwargs)

        # parse options using getopt
        try:
            opts, args = getopt.getopt(in_args, self.get_short(),
                                       self.get_long())
        except Exception, error:
            msg = "Error parsing %s for '%s': %s (parsing options: %s)"
            raise CmdParseError(msg % (self._type, self.name,
                                       str(error), in_args))

        # update params with values from command line
        for opt, val in opts:
            this, inverse = self.get_option(opt)
            if this['type'] is bool:
                params[this['name']] = not inverse
            else:
                try:
                    params[this['name']] = this['type'](val)
                except ValueError, exception:
                    msg = "Error parsing parameter '%s' %s.\n%s\n"
                    raise CmdParseError(msg % (this['name'], this['type'],
                                               str(exception)))

        return params, args


    def __call__(self, in_args, **kwargs):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of do_cmd
        """
        params, args = self.parse(in_args, **kwargs)
        return self.do_cmd(params, args)


class TaskOption(Command):
    """Process string with command options (for tasks)"""
    _type = "Task option"
