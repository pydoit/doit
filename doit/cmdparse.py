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
        dict.__setitem__(self, key, value)

    def update_defaults(self, update_dict):
        """do not update items that already have a non-default value"""
        for k,v in update_dict.iteritems():
            if k in self._non_default_keys:
                continue
            self[k] = v

    def __setitem__(self, key, value):
        self._non_default_keys.add(key)
        dict.__setitem__(self, key, value)


class CmdParseError(Exception):
    """Error parsing options """


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
    _type = "Command option"
    # description can be None or string. other fields must be string.
    _doc_fields = ('purpose', 'usage', 'description')
    _option_fields = ('name', 'default', 'short', 'long', 'type', 'help')
    # default values for option meta data
    _defaults = {'short': '',
                 'long': '',
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
                    raise CmdParseError(msg % (self._type ,self.name, field))

            # options can not contain any unrecognized field
            for field in opt.keys():
                if field not in self._option_fields:
                    msg = "%s dict from '%s' contains invalid property '%s'"
                    raise CmdParseError(msg % (self._type ,self.name, field))

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
            long_name = opt['long']
            if not long_name:
                continue
            # '=' means option takes a value
            if opt['type'] is not bool:
                long_name += '='
            long_list.append(long_name)
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
        params = DefaultUpdate()
        # add default values
        for opt in self.options:
            params.set_default(opt['name'], opt.get('default', None))

        # global parameters (got from main command options)
        params.update(kwargs)

        # parse options using getopt
        try:
            opts,args = getopt.getopt(in_args,self.get_short(),self.get_long())
        except Exception, e:
            msg = "Error parsing %s for '%s': %s (parsing options: %s)"
            raise CmdParseError(msg % (self._type, self.name, str(e), in_args))

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


class TaskOption(Command):
    _type = "Task option"
