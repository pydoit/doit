"""Parse command line options and execute it.

Built on top of getopt. optparse can't handle sub-commands.
"""
import os
import getopt
import copy
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Union



class DefaultUpdate(dict):
    """A dictionary that has an "update_defaults" method where
    only items with default values are updated.

    This is used when you have a dict that has multiple source of values
    (i.e. hardcoded, config file, command line). And values are updated
    beginning from the source with higher priority.

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
        for key, value in source.items():
            if key not in self:
                self.set_default(key, value)

    def update_defaults(self, update_dict):
        """like dict.update but do not update items that have
        a non-default value"""
        for key, value in update_dict.items():
            if key in self._non_default_keys:
                continue
            self.set_default(key, value)

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


@dataclass
class CmdOption:
    """A command line option.

    Can be created as a dataclass with keyword arguments, or from a dict
    using CmdOption.from_dict() or normalize_option() for backward compatibility.

    Attributes:
        name: Variable name for this option
        default: Default value (must match type)
        type: Type of the variable (str, int, bool, list). For bool, the option
              is a flag that sets the value to True when present.
        short: Short option name (e.g., 'v' for -v). Field metadata documents meaning.
        long: Long option name (e.g., 'verbosity' for --verbosity)
        inverse: Long name for inverse boolean flag (e.g., 'no-continue')
        choices: Dict of choice name -> description for valid values
        help: Help text for the option
        section: Meta info for grouping entries in help output
        metavar: Placeholder shown in help (e.g., 'ARG' in --file=ARG)
        env_var: Environment variable to read default from

    Example usage with field metadata:
        opt_verbosity = CmdOption(
            name='verbosity',
            default=None,
            type=int,
            short='v',   # v for verbosity level
            long='verbosity',
            help='0=capture all, 1=capture stdout, 2=print all',
        )
    """

    name: str = field(metadata={'doc': 'Variable name for this option'})
    default: Any = field(metadata={'doc': 'Default value'})
    type: type = field(default=str, metadata={'doc': 'Type (str, int, bool, list)'})
    short: str = field(default='', metadata={'doc': 'Short option (e.g., "v" for -v)'})
    long: str = field(default='', metadata={'doc': 'Long option (e.g., "verbosity")'})
    inverse: str = field(default='', metadata={'doc': 'Inverse boolean flag name'})
    choices: dict = field(default_factory=dict, metadata={'doc': 'Valid choices'})
    help: str = field(default='', metadata={'doc': 'Help text'})
    section: str = field(default='', metadata={'doc': 'Help section grouping'})
    metavar: str = field(default='ARG', metadata={'doc': 'Argument placeholder'})
    env_var: Optional[str] = field(default=None, metadata={'doc': 'Environment variable'})

    def __post_init__(self):
        """Handle list defaults and choice conversion."""
        if self.type is list and self.default is not None:
            self.default = copy.copy(self.default)
        # Convert choices from list of tuples to dict if needed
        if isinstance(self.choices, list):
            self.choices = dict(self.choices)

    @classmethod
    def from_dict(cls, opt_dict: dict) -> 'CmdOption':
        """Create CmdOption from a dictionary (backward compatibility).

        @param opt_dict: Dictionary with option properties
        @return: CmdOption instance
        @raise CmdParseError: If required fields missing or unknown fields present
        """
        opt_dict = opt_dict.copy()

        # Validate required fields
        for required in ('name', 'default'):
            if required not in opt_dict:
                msg = "CmdOption dict %r missing required property '%s'"
                raise CmdParseError(msg % (opt_dict, required))

        # Extract known fields with defaults
        name = opt_dict.pop('name')
        default = opt_dict.pop('default')
        opt_type = opt_dict.pop('type', str)
        short = opt_dict.pop('short', '')
        long = opt_dict.pop('long', '')
        inverse = opt_dict.pop('inverse', '')
        choices = opt_dict.pop('choices', [])
        help_text = opt_dict.pop('help', '')
        section = opt_dict.pop('section', '')
        metavar = opt_dict.pop('metavar', 'ARG')
        env_var = opt_dict.pop('env_var', None)

        # Reject unknown fields
        if opt_dict:
            msg = "CmdOption dict contains invalid property '%s'"
            raise CmdParseError(msg % list(opt_dict.keys()))

        return cls(
            name=name,
            default=default,
            type=opt_type,
            short=short,
            long=long,
            inverse=inverse,
            choices=choices if isinstance(choices, dict) else dict(choices),
            help=help_text,
            section=section,
            metavar=metavar,
            env_var=env_var,
        )

    def __repr__(self):
        return (f"{self.__class__.__name__}({{'name':{self.name!r}, "
                f"'short':{self.short!r},'long':{self.long!r} }})")

    def set_default(self, val):
        """Set default value, value is already the expected type."""
        if self.type is list:
            self.default = copy.copy(val)
        else:
            self.default = val

    def validate_choice(self, given_value):
        """Raise error if value is not a valid choice."""
        if given_value not in self.choices:
            msg = ("Error parsing parameter '{}'. "
                   "Provided '{}' but available choices are: {}.")
            choices = ", ".join(f"'{k}'" for k in self.choices.keys())
            raise CmdParseError(msg.format(self.name, given_value, choices))

    _boolean_states = {
        '1': True, 'yes': True, 'true': True, 'on': True,
        '0': False, 'no': False, 'false': False, 'off': False,
    }

    def str2boolean(self, str_val):
        """Convert string to boolean."""
        try:
            return self._boolean_states[str_val.lower()]
        except Exception:
            raise ValueError('Not a boolean: {}'.format(str_val))

    def str2type(self, str_val):
        """Convert string value to option type value."""
        try:
            # no conversion if value is not a string
            if not isinstance(str_val, str):
                val = str_val
            elif self.type is bool:
                val = self.str2boolean(str_val)
            elif self.type is list:
                parts = [p.strip() for p in str_val.split(',')]
                val = [p for p in parts if p]  # remove empty strings
            else:
                val = self.type(str_val)
        except ValueError as exception:
            msg = (f"Error parsing parameter '{self.name}' {self.type}.\n"
                   f"{exception}\n")
            raise CmdParseError(msg)

        if self.choices:
            self.validate_choice(val)
        return val


    @staticmethod
    def _print_2_columns(col1, col2):
        """print using a 2-columns format """
        column1_len = 24
        column2_start = 28
        left = (col1).ljust(column1_len)
        right = col2.replace('\n', '\n' + column2_start * ' ')
        return "  %s  %s" % (left, right)

    def help_param(self):
        """return string of option's short and long name
        i.e.:   -f ARG, --file=ARG
        """
        opts_str = []
        if self.short:
            if self.type is bool:
                opts_str.append('-%s' % self.short)
            else:
                opts_str.append('-%s %s' % (self.short, self.metavar))
        if self.long:
            if self.type is bool:
                opts_str.append('--%s' % self.long)
            else:
                opts_str.append('--%s=%s' % (self.long, self.metavar))
        return ', '.join(opts_str)

    def help_choices(self):
        """return string with help for option choices"""
        if not self.choices:
            return ''

        # if choice has a description display one choice per line...
        if any(self.choices.values()):
            items = []
            for choice in sorted(self.choices):
                items.append("\n{}: {}".format(choice, self.choices[choice]))
            return "\nchoices:" + "".join(items)
        # ... otherwise display in a single line
        else:
            return "\nchoices: " + ", ".join(sorted(self.choices.keys()))


    def help_doc(self):
        """return list of string of option's help doc

        Note this is used only to display help on tasks.
        For commands a better and more complete version is used.
        see cmd_base:Command.help
        """
        # ignore option that cant be modified on cmd line
        if not (self.short or self.long):
            return []

        text = []
        opt_str = self.help_param()
        # TODO It should always display option's default value
        opt_help = self.help % {'default': self.default}
        opt_choices = self.help_choices()
        opt_config = 'config: {}'.format(self.name)
        opt_env = ', environ: {}'.format(self.env_var) if self.env_var else ''

        desc = f'{opt_help} {opt_choices} ({opt_config}{opt_env})'
        text.append(self._print_2_columns(opt_str, desc))
        # print bool inverse option
        if self.inverse:
            opt_str = '--%s' % self.inverse
            opt_help = 'opposite of --%s' % self.long
            text.append(self._print_2_columns(opt_str, opt_help))
        return text


def normalize_option(opt: Union[dict, 'CmdOption']) -> CmdOption:
    """Convert option to CmdOption if it's a dict.

    @param opt: Either a dict with option properties or a CmdOption instance
    @return: CmdOption instance
    """
    if isinstance(opt, dict):
        return CmdOption.from_dict(opt)
    return opt


class CmdParse(object):
    """Process string with command options

    @ivar options: (list - CmdOption)
    """
    _type = "Command"

    def __init__(self, options):
        self._options = OrderedDict((o.name, o) for o in options)

    def __contains__(self, key):
        return key in self._options

    def __getitem__(self, key):
        return self._options[key]

    @property
    def options(self):
        """return list of options for backward compatibility"""
        return list(self._options.values())

    def get_short(self):
        """return string with short options for getopt"""
        short_list = ""
        for opt in self._options.values():
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
        for opt in self._options.values():
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
            - CmdOption from matching opt_str. or None
            - (bool) matched inverse
        """
        for opt in self._options.values():
            if opt_str in ('-' + opt.short, '--' + opt.long):
                return opt, False
            if opt_str == '--' + opt.inverse:
                return opt, True
        return None, None

    def overwrite_defaults(self, new_defaults):
        """overwrite self.options default values

        This values typically come from an INI file
        """
        for key, val in new_defaults.items():
            if key in self._options:
                opt = self._options[key]
                opt.set_default(opt.str2type(val))


    def parse_only(self, in_args, params=None):
        """parse arguments into options(params) and positional arguments

        @param in_args (list - string): typically sys.argv[1:]
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             pos_args (list - string): positional arguments
        """
        params = params if params else {}

        # parse cmdline options using getopt
        try:
            opts, args = getopt.getopt(in_args, self.get_short(),
                                       self.get_long())
        except Exception as error:
            msg = (f"Error parsing {self._type}: {error} "
                   f"(parsing options: {self.options}). Got: {in_args}")
            raise CmdParseError(msg)

        # update params with values from command line
        for opt, val in opts:
            this, inverse = self.get_option(opt)
            if this.type is bool:
                params[this.name] = not inverse
            elif this.type is list:
                params[this.name].append(val)
            else:
                params[this.name] = this.str2type(val)

        return params, args


    def parse(self, in_args):
        """parse arguments into options(params) and positional arguments

        Also get values from shell ENV.

        Returned params is a `DefaultUpdate` type and includes
        an item for every option.

        @param in_args (list - string): typically sys.argv[1:]
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             pos_args (list - string): positional arguments
        """
        params = DefaultUpdate()
        # add default values
        for opt in self._options.values():
            params.set_default(opt.name, opt.default)

        # get values from shell ENV
        for opt in self._options.values():
            if opt.env_var:
                val = os.getenv(opt.env_var)
                if val is not None:
                    params[opt.name] = opt.str2type(val)

        return self.parse_only(in_args, params)



class TaskParse(CmdParse):
    """Process string with command options (for tasks)"""
    _type = "Task"
