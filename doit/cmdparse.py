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

        # options can not contain any unrecognized field
        if opt_dict:
            msg = "CmdOption dict contains invalid property '%s'"
            raise CmdParseError(msg % opt_dict.keys())


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

    def parse(self, in_args, **kwargs):
        """parse arguments into options(params) and positional arguments

        @param in_args (list - string): typically sys.argv[1:]
        @param kwargs: apart from options some "extra" values can be passed to
                       the command.
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             pos_args (list - string): positional arguments
        """
        params = DefaultUpdate()
        # add default values
        for opt in self.options:
            params.set_default(opt.name, opt.default)

        # global parameters (got from main command options)
        params.update(kwargs)

        # parse options using getopt
        try:
            opts, args = getopt.getopt(in_args, self.get_short(),
                                       self.get_long())
        except Exception, error:
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
                except ValueError, exception:
                    msg = "Error parsing parameter '%s' %s.\n%s\n"
                    raise CmdParseError(msg % (this.name, this.type,
                                               str(exception)))

        return params, args



class TaskParse(CmdParse):
    """Process string with command options (for tasks)"""
    _type = "Task"
