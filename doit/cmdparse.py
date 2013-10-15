"""Parse command line options and execute it.

Built on top of getopt. optparse can't handle sub-commands.
"""
import getopt
import six


class DefaultUpdate(dict):
    """A dictionary that has an "update_defaults" method where
    only items with default values are updated.

    This is used when you have a dict that has multiple source of values
    (i.e. hardcoded, config file, command line). And values are updated
    beggining from the source with higher priority.

    A default value is added with the method set_default or add_defaults.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        # set of keys that have a non-default value
        self._non_default_keys = set()

    def set_default(self, key, value):
        """set default value for given key"""
        dict.__setitem__(self, key, value)

    def add_defaults(self, source):
        """add default values from another dict
        @param source: (dict)"""
        for key, value in six.iteritems(source):
            if key not in self:
                self.set_default(key, value)

    def update_defaults(self, update_dict):
        """like dict.update but do not update items that have
        a non-default value"""
        for key, value in six.iteritems(update_dict):
            if key in self._non_default_keys:
                continue
            self[key] = value

    def __setitem__(self, key, value):
        """overwrite to keep track of _non_default_keys"""
        try:
            self._non_default_keys.add(key)
        # http://bugs.python.org/issue826897
        except AttributeError:
            self._non_default_keys = set()
            self._non_default_keys.add(key)
        dict.__setitem__(self, key, value)


class CmdParseError(Exception):
    """Error parsing options """


class CmdOption(object):
    """a command line option

       - name (string) : variable name
       - default (value from its type): default value
       - type (type): type of the variable. must be able to be initialized
                      taking a single string parameter.
                      if type is bool. option is just a flag. and if present
                      its value is set to True.
       - short (string): argument short name
       - long (string): argument long name
       - inverse (string): argument long name to be the inverse of the default
                           value (only used by boolean options)
       - help (string): option description
    """

    def __init__(self, opt_dict):
        # options must contain 'name' and 'default' value
        opt_dict = opt_dict.copy()
        for field in ('name', 'default',):
            if field not in opt_dict:
                msg = "CmdOption dict %r missing required property '%s'"
                raise CmdParseError(msg % (opt_dict, field))

        self.name = opt_dict.pop('name')
        self.default = opt_dict.pop('default')
        self.type = opt_dict.pop('type', str)
        self.short = opt_dict.pop('short', '')
        self.long = opt_dict.pop('long', '')
        self.inverse = opt_dict.pop('inverse', '')
        self.help = opt_dict.pop('help', '')

        # TODO support "choice"
        # TODO add some hint for tab-completion scripts

        # options can not contain any unrecognized field
        if opt_dict:
            msg = "CmdOption dict contains invalid property '%s'"
            raise CmdParseError(msg % list(six.iterkeys(opt_dict)))


    def __repr__(self):
        tmpl = ("{0}({{'name':{1.name!r}, 'short':{1.short!r}," +
                "'long':{1.long!r} }})")
        return tmpl.format(self.__class__.__name__, self)

    @staticmethod
    def _print_2_columns(col1, col2):
        """print using a 2-columns format """
        column1_len = 24
        column2_start = 28
        left = (col1).ljust(column1_len)
        right = col2.replace('\n', '\n'+ column2_start * ' ')
        return "  %s  %s" % (left, right)

    def help_param(self):
        """return string of option's short and long name
        i.e.:   -f ARG, --file=ARG
        """
        # TODO replace 'ARG' with metavar (copy from optparse)
        opts_str = []
        if self.short:
            if self.type is bool:
                opts_str.append('-%s' % self.short)
            else:
                opts_str.append('-%s ARG' % self.short)
        if self.long:
            if self.type is bool:
                opts_str.append('--%s' % self.long)
            else:
                opts_str.append('--%s=ARG' % self.long)
        return ', '.join(opts_str)


    def help_doc(self):
        """return list of string of option's help doc"""
        # ignore option that cant be modified on cmd line
        if not (self.short or self.long):
            return []

        text = []
        opt_str = self.help_param()
        opt_help = self.help % {'default': self.default}
        text.append(self._print_2_columns(opt_str, opt_help))
        # print bool inverse option
        if self.inverse:
            opt_str = '--%s' % self.inverse
            opt_help = 'opposite of --%s' % self.long
            text.append(self._print_2_columns(opt_str, opt_help))
        return text



class CmdParse(object):
    """Process string with command options

    @ivar options: (list - CmdOption)
    """
    _type = "Command"

    def __init__(self, options):
        self.options = options[:]

    def get_short(self):
        """return string with short options for getopt"""
        short_list = ""
        for opt in self.options:
            if not opt.short:
                continue
            short_list += opt.short
            # ':' means option takes a value
            if opt.type is not bool:
                short_list += ':'
        return short_list

    def get_long(self):
        """return list with long options for getopt"""
        long_list = []
        for opt in self.options:
            long_name = opt.long
            if not long_name:
                continue
            # '=' means option takes a value
            if opt.type is not bool:
                long_name += '='
            long_list.append(long_name)
            if opt.inverse:
                long_list.append(opt.inverse)
        return long_list

    def get_option(self, opt_str):
        """return tuple
            - option dictionary from matching opt_str. or None
            - (bool) matched inverse
        """
        for opt in self.options:
            if opt_str in ('-' + opt.short, '--' + opt.long):
                return opt, False
            if opt_str == '--' + opt.inverse:
                return opt, True
        return None, None

    def parse(self, in_args):
        """parse arguments into options(params) and positional arguments

        @param in_args (list - string): typically sys.argv[1:]
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             pos_args (list - string): positional arguments
        """
        params = DefaultUpdate()
        # add default values
        for opt in self.options:
            params.set_default(opt.name, opt.default)

        # parse options using getopt
        try:
            opts, args = getopt.getopt(in_args, self.get_short(),
                                       self.get_long())
        except Exception as error:
            msg = "Error parsing %s: %s (parsing options: %s)"
            raise CmdParseError(msg % (self._type, str(error), in_args))

        # update params with values from command line
        for opt, val in opts:
            this, inverse = self.get_option(opt)
            if this.type is bool:
                params[this.name] = not inverse
            else:
                try:
                    params[this.name] = this.type(val)
                except ValueError as exception:
                    msg = "Error parsing parameter '%s' %s.\n%s\n"
                    raise CmdParseError(msg % (this.name, this.type,
                                               str(exception)))

        return params, args



class TaskParse(CmdParse):
    """Process string with command options (for tasks)"""
    _type = "Task"
