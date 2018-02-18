import os
import pickle

import pytest

from doit.cmdparse import DefaultUpdate, CmdParseError, CmdOption, CmdParse



class TestDefaultUpdate(object):
    def test(self):
        du = DefaultUpdate()

        du.set_default('a', 0)
        du.set_default('b', 0)

        assert 0 == du['a']
        assert 0 == du['b']

        # set b with non-default value
        du['b'] = 1
        # only a is update
        du.update_defaults({'a':2, 'b':2})
        assert 2 == du['a']
        assert 1 == du['b']

        # default for `a` can be updated again
        du.update_defaults({'a':3})
        assert 3 == du['a']


    def test_add_defaults(self):
        du = DefaultUpdate()
        du.add_defaults({'a': 0, 'b':1})
        du['c'] = 5
        du.add_defaults({'a':2, 'c':2})
        assert 0 == du['a']
        assert 1 == du['b']
        assert 5 == du['c']

    # http://bugs.python.org/issue826897
    def test_pickle(self):
        du = DefaultUpdate()
        du.set_default('x', 0)
        dump = pickle.dumps(du,2)
        pickle.loads(dump)


class TestCmdOption(object):

    def test_repr(self):
        opt = CmdOption({'name':'opt1', 'default':'',
                         'short':'o', 'long':'other'})
        assert "CmdOption(" in repr(opt)
        assert "'name':'opt1'" in repr(opt)
        assert "'short':'o'" in repr(opt)
        assert "'long':'other'" in repr(opt)

    def test_non_required_fields(self):
        opt1 = CmdOption({'name':'op1', 'default':''})
        assert '' == opt1.long

    def test_invalid_field(self):
        opt_dict = {'name':'op1', 'default':'', 'non_existent':''}
        pytest.raises(CmdParseError, CmdOption, opt_dict)

    def test_missing_field(self):
        opt_dict = {'name':'op1', 'long':'abc'}
        pytest.raises(CmdParseError, CmdOption, opt_dict)


class TestCmdOption_str2val(object):
    def test_str2boolean(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool,
                         'short':'b', 'long': 'bobo'})
        assert True == opt.str2boolean('1')
        assert True == opt.str2boolean('yes')
        assert True == opt.str2boolean('Yes')
        assert True == opt.str2boolean('YES')
        assert True == opt.str2boolean('true')
        assert True == opt.str2boolean('on')
        assert False == opt.str2boolean('0')
        assert False == opt.str2boolean('false')
        assert False == opt.str2boolean('no')
        assert False == opt.str2boolean('off')
        assert False == opt.str2boolean('OFF')
        pytest.raises(ValueError, opt.str2boolean, '2')
        pytest.raises(ValueError, opt.str2boolean, None)
        pytest.raises(ValueError, opt.str2boolean, 'other')


    def test_non_string_values_are_not_converted(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool})
        assert False == opt.str2type(False)
        assert True == opt.str2type(True)
        assert None == opt.str2type(None)

    def test_str(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':str})
        assert 'foo' == opt.str2type('foo')
        assert 'bar' == opt.str2type('bar')

    def test_bool(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool})
        assert False == opt.str2type('off')
        assert True == opt.str2type('on')

    def test_int(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':int})
        assert 2 == opt.str2type('2')
        assert -3 == opt.str2type('-3')

    def test_list(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':list})
        assert ['foo'] == opt.str2type('foo')
        assert [] == opt.str2type('')
        assert ['foo', 'bar'] == opt.str2type('foo , bar ')

    def test_invalid_value(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':int})
        pytest.raises(CmdParseError, opt.str2type, 'not a number')


class TestCmdOption_help_param(object):
    def test_bool_param(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':bool,
                          'short':'b', 'long': 'bobo'})
        assert '-b, --bobo' == opt1.help_param()

    def test_non_bool_param(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':str,
                          'short':'s', 'long': 'susu'})
        assert '-s ARG, --susu=ARG' == opt1.help_param()


    def test_no_long(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':str,
                          'short':'s'})
        assert '-s ARG' == opt1.help_param()


opt_bool = {'name': 'flag',
            'short':'f',
            'long': 'flag',
            'inverse':'no-flag',
            'type': bool,
            'default': False,
            'help': 'help for opt1'}

opt_rare = {'name': 'rare_bool',
            'long': 'rare-bool',
            'env_var': 'RARE',
            'type': bool,
            'default': False,
            'help': 'help for opt2',}

opt_int = {'name': 'num',
           'short':'n',
           'long': 'number',
           'type': int,
           'default': 5,
           'help': 'help for opt3'}

opt_no = {'name': 'no',
          'short':'',
          'long': '',
          'type': int,
          'default': 5,
          'help': 'user cant modify me'}

opt_append = { 'name': 'list',
             'short': 'l',
             'long': 'list',
             'type': list,
             'default': [],
             'help': 'use many -l to make a list'}

opt_choices_desc = {'name': 'choices',
                    'short':'c',
                    'long': 'choice',
                    'type': str,
                    'choices': (("yes", "signify affirmative"),
                                ("no","signify negative")),
                    'default': "yes",
                    'help': 'User chooses [default %(default)s]'}

opt_choices_nodesc = {'name': 'choicesnodesc',
                      'short':'C',
                      'long': 'achoice',
                      'type': str,
                      'choices': (("yes", ""),
                                  ("no", "")),
                      'default': "no",
                      'help': 'User chooses [default %(default)s]'}


class TestCmdOption_help_doc(object):
    def test_param(self):
        opt1 = CmdOption(opt_bool)
        got = opt1.help_doc()
        assert '-f, --flag' in got[0]
        assert 'help for opt1' in got[0]
        assert '--no-flag' in got[1]
        assert 2 == len(got)

    def test_no_doc_param(self):
        opt1 = CmdOption(opt_no)
        assert 0 == len(opt1.help_doc())

    def test_choices_desc_doc(self):
        the_opt = CmdOption(opt_choices_desc)
        doc = the_opt.help_doc()[0]
        assert 'choices:\n' in doc
        assert 'yes: signify affirmative' in doc
        assert 'no: signify negative' in doc

    def test_choices_nodesc_doc(self):
        the_opt = CmdOption(opt_choices_nodesc)
        doc = the_opt.help_doc()[0]
        assert "choices: no, yes" in doc

    def test_name_config_env(self):
        opt1 = CmdOption(opt_rare)
        got = opt1.help_doc()
        assert 'config: rare_bool' in got[0]
        assert 'environ: RARE' in got[0]



class TestCommand(object):

    @pytest.fixture
    def cmd(self, request):
        opt_list = (opt_bool, opt_rare, opt_int, opt_no,
                    opt_append, opt_choices_desc, opt_choices_nodesc)
        options = [CmdOption(o) for o in opt_list]
        cmd = CmdParse(options)
        return cmd

    def test_contains(self, cmd):
        assert 'flag' in cmd
        assert 'num' in cmd
        assert 'xxx' not in cmd

    def test_getitem(self, cmd):
        assert cmd['flag'].short == 'f'
        assert cmd['num'].default == 5

    def test_option_list(self, cmd):
        opt_names = [o.name for o in cmd.options]
        assert  ['flag', 'rare_bool', 'num', 'no', 'list', 'choices',
                 'choicesnodesc']== opt_names

    def test_short(self, cmd):
        assert "fn:l:c:C:" == cmd.get_short(), cmd.get_short()

    def test_long(self, cmd):
        longs = ["flag", "no-flag", "rare-bool", "number=",
                 "list=", "choice=", "achoice="]
        assert longs == cmd.get_long()

    def test_getOption(self, cmd):
        # short
        opt, is_inverse = cmd.get_option('-f')
        assert (opt_bool['name'], False) == (opt.name, is_inverse)
        # long
        opt, is_inverse = cmd.get_option('--rare-bool')
        assert (opt_rare['name'], False) == (opt.name, is_inverse)
        # inverse
        opt, is_inverse = cmd.get_option('--no-flag')
        assert (opt_bool['name'], True) == (opt.name, is_inverse)
        # not found
        opt, is_inverse = cmd.get_option('not-there')
        assert (None, None) == (opt, is_inverse)

        opt, is_inverse = cmd.get_option('--list')
        assert (opt_append['name'], False) == (opt.name, is_inverse)

        opt, is_inverse = cmd.get_option('--choice')
        assert (opt_choices_desc['name'], False) == (opt.name, is_inverse)

        opt, is_inverse = cmd.get_option('--achoice')
        assert (opt_choices_nodesc['name'], False) == (opt.name, is_inverse)


    def test_parseDefaults(self, cmd):
        params, args = cmd.parse([])
        assert False == params['flag']
        assert 5 == params['num']
        assert [] == params['list']
        assert "yes" == params['choices']
        assert "no" == params['choicesnodesc']

    def test_overwrite_defaults(self, cmd):
        cmd.overwrite_defaults({'num': 9, 'i_dont_exist': 1})
        params, args = cmd.parse([])
        assert 9 == params['num']

    def test_overwrite_defaults_convert_type(self, cmd):
        cmd.overwrite_defaults({'num': '9', 'list': 'foo, bar', 'flag':'on'})
        params, args = cmd.parse([])
        assert 9 == params['num']
        assert ['foo', 'bar'] == params['list']
        assert True == params['flag']

    def test_parseShortValues(self, cmd):
        params, args = cmd.parse(['-n','89','-f', '-l', 'foo', '-l', 'bar',
                                  '-c', 'no', '-C', 'yes'])
        assert True == params['flag']
        assert 89 == params['num']
        assert ['foo', 'bar'] == params['list']
        assert "no" == params['choices']
        assert "yes" == params['choicesnodesc']

    def test_parseLongValues(self, cmd):
        params, args = cmd.parse(['--rare-bool','--num','89', '--no-flag',
                                  '--list', 'flip', '--list', 'flop',
                                  '--choice', 'no', '--achoice', 'yes'])
        assert True == params['rare_bool']
        assert False == params['flag']
        assert 89 == params['num']
        assert ['flip', 'flop'] == params['list']
        assert "no" == params['choices']
        assert "yes" == params['choicesnodesc']

    def test_parsePositionalArgs(self, cmd):
        params, args = cmd.parse(['-f','p1','p2', '--sub-arg'])
        assert ['p1','p2', '--sub-arg'] == args

    def test_parseError(self, cmd):
        pytest.raises(CmdParseError, cmd.parse, ['--not-exist-param'])

    def test_parseWrongType(self, cmd):
        pytest.raises(CmdParseError, cmd.parse, ['--num','oi'])

    def test_parseWrongChoice(self, cmd):
        pytest.raises(CmdParseError, cmd.parse, ['--choice', 'maybe'])

    def test_env_val(self):
        opt_foo = {
            'name': 'foo',
            'long': 'foo',
            'type': str,
            'env_var': 'FOO',
            'default': 'zero'
        }
        cmd = CmdParse([CmdOption(opt_foo)])

        # get default
        params, args = cmd.parse([])
        assert params['foo'] == 'zero'

        # get from env
        os.environ['FOO'] = 'bar'
        params2, args2 = cmd.parse([])
        assert params2['foo'] == 'bar'

        # command line has precedence
        params2, args2 = cmd.parse(['--foo', 'XXX'])
        assert params2['foo'] == 'XXX'


    def test_env_val_bool(self):
        opt_foo = {
            'name': 'foo',
            'long': 'foo',
            'type': bool,
            'env_var': 'FOO',
            'default': False,
        }
        cmd = CmdParse([CmdOption(opt_foo)])

        # get from env
        os.environ['FOO'] = '1'
        params, args = cmd.parse([])
        assert params['foo'] == True

        # get from env
        os.environ['FOO'] = '0'
        params, args = cmd.parse([])
        assert params['foo'] == False
