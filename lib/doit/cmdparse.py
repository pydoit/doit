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
    @ivar do_cmd (callable): function must have 2 parameters. it will be called
                             with the result of the parse method.
    """

    def __init__(self, name, options, do_cmd):
        self.name = name
        self.options = options
        self.do_cmd = do_cmd

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
        try:
            opts,args = getopt.getopt(in_args,self.get_short(),self.get_long())
        except getopt.GetoptError, err:
            print str(err)
            print "not like this %s" % self.name
            return #FIXME TODO

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
