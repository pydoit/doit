import os
import pickle
import unittest

from doit.cmdparse import DefaultUpdate, CmdParseError, CmdOption, CmdParse


class TestDefaultUpdate(unittest.TestCase):
    def test(self):
        du = DefaultUpdate()

        du.set_default('a', 0)
        du.set_default('b', 0)

        self.assertEqual(0, du['a'])
        self.assertEqual(0, du['b'])

        # set b with non-default value
        du['b'] = 1
        # only a is update
        du.update_defaults({'a':2, 'b':2})
        self.assertEqual(2, du['a'])
        self.assertEqual(1, du['b'])

        # default for `a` can be updated again
        du.update_defaults({'a':3})
        self.assertEqual(3, du['a'])


    def test_add_defaults(self):
        du = DefaultUpdate()
        du.add_defaults({'a': 0, 'b':1})
        du['c'] = 5
        du.add_defaults({'a':2, 'c':2})
        self.assertEqual(0, du['a'])
        self.assertEqual(1, du['b'])
        self.assertEqual(5, du['c'])

    # http://bugs.python.org/issue826897
    def test_pickle(self):
        du = DefaultUpdate()
        du.set_default('x', 0)
        dump = pickle.dumps(du, 2)
        pickle.loads(dump)


class TestCmdOption(unittest.TestCase):

    def test_repr(self):
        opt = CmdOption({'name':'opt1', 'default':'',
                         'short':'o', 'long':'other'})
        self.assertIn("CmdOption(", repr(opt))
        self.assertIn("'name':'opt1'", repr(opt))
        self.assertIn("'short':'o'", repr(opt))
        self.assertIn("'long':'other'", repr(opt))

    def test_non_required_fields(self):
        opt1 = CmdOption({'name':'op1', 'default':''})
        self.assertEqual('', opt1.long)

    def test_invalid_field(self):
        opt_dict = {'name':'op1', 'default':'', 'non_existent':''}
        self.assertRaises(CmdParseError, CmdOption, opt_dict)

    def test_missing_field(self):
        opt_dict = {'name':'op1', 'long':'abc'}
        self.assertRaises(CmdParseError, CmdOption, opt_dict)


class TestCmdOption_str2val(unittest.TestCase):
    def test_str2boolean(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool,
                         'short':'b', 'long': 'bobo'})
        self.assertTrue(opt.str2boolean('1'))
        self.assertTrue(opt.str2boolean('yes'))
        self.assertTrue(opt.str2boolean('Yes'))
        self.assertTrue(opt.str2boolean('YES'))
        self.assertTrue(opt.str2boolean('true'))
        self.assertTrue(opt.str2boolean('on'))
        self.assertFalse(opt.str2boolean('0'))
        self.assertFalse(opt.str2boolean('false'))
        self.assertFalse(opt.str2boolean('no'))
        self.assertFalse(opt.str2boolean('off'))
        self.assertFalse(opt.str2boolean('OFF'))
        self.assertRaises(ValueError, opt.str2boolean, '2')
        self.assertRaises(ValueError, opt.str2boolean, None)
        self.assertRaises(ValueError, opt.str2boolean, 'other')


    def test_non_string_values_are_not_converted(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool})
        self.assertFalse(opt.str2type(False))
        self.assertTrue(opt.str2type(True))
        self.assertIsNone(opt.str2type(None))

    def test_str(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':str})
        self.assertEqual('foo', opt.str2type('foo'))
        self.assertEqual('bar', opt.str2type('bar'))

    def test_bool(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':bool})
        self.assertFalse(opt.str2type('off'))
        self.assertTrue(opt.str2type('on'))

    def test_int(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':int})
        self.assertEqual(2, opt.str2type('2'))
        self.assertEqual(-3, opt.str2type('-3'))

    def test_list(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':list})
        self.assertEqual(['foo'], opt.str2type('foo'))
        self.assertEqual([], opt.str2type(''))
        self.assertEqual(['foo', 'bar'], opt.str2type('foo , bar '))

    def test_invalid_value(self):
        opt = CmdOption({'name':'op1', 'default':'', 'type':int})
        self.assertRaises(CmdParseError, opt.str2type, 'not a number')


class TestCmdOption_help_param(unittest.TestCase):
    def test_bool_param(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':bool,
                          'short':'b', 'long': 'bobo'})
        self.assertEqual('-b, --bobo', opt1.help_param())

    def test_non_bool_param(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':str,
                          'short':'s', 'long': 'susu'})
        self.assertEqual('-s ARG, --susu=ARG', opt1.help_param())

    def test_metavar(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':str, 'metavar':'VAL',
                          'short':'s', 'long': 'susu'})
        self.assertEqual('-s VAL, --susu=VAL', opt1.help_param())

    def test_no_long(self):
        opt1 = CmdOption({'name':'op1', 'default':'', 'type':str,
                          'short':'s'})
        self.assertEqual('-s ARG', opt1.help_param())


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


class TestCmdOption_help_doc(unittest.TestCase):
    def test_param(self):
        opt1 = CmdOption(opt_bool)
        got = opt1.help_doc()
        self.assertIn('-f, --flag', got[0])
        self.assertIn('help for opt1', got[0])
        self.assertIn('--no-flag', got[1])
        self.assertEqual(2, len(got))

    def test_no_doc_param(self):
        opt1 = CmdOption(opt_no)
        self.assertEqual(0, len(opt1.help_doc()))

    def test_choices_desc_doc(self):
        the_opt = CmdOption(opt_choices_desc)
        doc = the_opt.help_doc()[0]
        self.assertIn('choices:\n', doc)
        self.assertIn('yes: signify affirmative', doc)
        self.assertIn('no: signify negative', doc)

    def test_choices_nodesc_doc(self):
        the_opt = CmdOption(opt_choices_nodesc)
        doc = the_opt.help_doc()[0]
        self.assertIn("choices: no, yes", doc)

    def test_name_config_env(self):
        opt1 = CmdOption(opt_rare)
        got = opt1.help_doc()
        self.assertIn('config: rare_bool', got[0])
        self.assertIn('environ: RARE', got[0])


class TestCommand(unittest.TestCase):

    def _make_cmd(self):
        opt_list = (opt_bool, opt_rare, opt_int, opt_no,
                    opt_append, opt_choices_desc, opt_choices_nodesc)
        options = [CmdOption(o) for o in opt_list]
        return CmdParse(options)

    def setUp(self):
        super().setUp()
        self.cmd = self._make_cmd()

    def test_contains(self):
        self.assertIn('flag', self.cmd)
        self.assertIn('num', self.cmd)
        self.assertNotIn('xxx', self.cmd)

    def test_getitem(self):
        self.assertEqual(self.cmd['flag'].short, 'f')
        self.assertEqual(self.cmd['num'].default, 5)

    def test_option_list(self):
        opt_names = [o.name for o in self.cmd.options]
        self.assertEqual(['flag', 'rare_bool', 'num', 'no', 'list', 'choices',
                          'choicesnodesc'], opt_names)

    def test_short(self):
        self.assertEqual("fn:l:c:C:", self.cmd.get_short())

    def test_long(self):
        longs = ["flag", "no-flag", "rare-bool", "number=",
                 "list=", "choice=", "achoice="]
        self.assertEqual(longs, self.cmd.get_long())

    def test_getOption(self):
        cmd = self.cmd
        # short
        opt, is_inverse = cmd.get_option('-f')
        self.assertEqual((opt_bool['name'], False), (opt.name, is_inverse))
        # long
        opt, is_inverse = cmd.get_option('--rare-bool')
        self.assertEqual((opt_rare['name'], False), (opt.name, is_inverse))
        # inverse
        opt, is_inverse = cmd.get_option('--no-flag')
        self.assertEqual((opt_bool['name'], True), (opt.name, is_inverse))
        # not found
        opt, is_inverse = cmd.get_option('not-there')
        self.assertEqual((None, None), (opt, is_inverse))

        opt, is_inverse = cmd.get_option('--list')
        self.assertEqual((opt_append['name'], False), (opt.name, is_inverse))

        opt, is_inverse = cmd.get_option('--choice')
        self.assertEqual((opt_choices_desc['name'], False), (opt.name, is_inverse))

        opt, is_inverse = cmd.get_option('--achoice')
        self.assertEqual((opt_choices_nodesc['name'], False), (opt.name, is_inverse))

    def test_parseDefaults(self):
        params, args = self.cmd.parse([])
        self.assertFalse(params['flag'])
        self.assertEqual(5, params['num'])
        self.assertEqual([], params['list'])
        self.assertEqual("yes", params['choices'])
        self.assertEqual("no", params['choicesnodesc'])

    def test_overwrite_defaults(self):
        self.cmd.overwrite_defaults({'num': 9, 'i_dont_exist': 1})
        params, args = self.cmd.parse([])
        self.assertEqual(9, params['num'])

    def test_overwrite_defaults_convert_type(self):
        self.cmd.overwrite_defaults({'num': '9', 'list': 'foo, bar', 'flag':'on'})
        params, args = self.cmd.parse([])
        self.assertEqual(9, params['num'])
        self.assertEqual(['foo', 'bar'], params['list'])
        self.assertTrue(params['flag'])

    def test_parseShortValues(self):
        params, args = self.cmd.parse(['-n','89','-f', '-l', 'foo', '-l', 'bar',
                                       '-c', 'no', '-C', 'yes'])
        self.assertTrue(params['flag'])
        self.assertEqual(89, params['num'])
        self.assertEqual(['foo', 'bar'], params['list'])
        self.assertEqual("no", params['choices'])
        self.assertEqual("yes", params['choicesnodesc'])

    def test_parseLongValues(self):
        params, args = self.cmd.parse(['--rare-bool','--num','89', '--no-flag',
                                       '--list', 'flip', '--list', 'flop',
                                       '--choice', 'no', '--achoice', 'yes'])
        self.assertTrue(params['rare_bool'])
        self.assertFalse(params['flag'])
        self.assertEqual(89, params['num'])
        self.assertEqual(['flip', 'flop'], params['list'])
        self.assertEqual("no", params['choices'])
        self.assertEqual("yes", params['choicesnodesc'])

    def test_parsePositionalArgs(self):
        params, args = self.cmd.parse(['-f','p1','p2', '--sub-arg'])
        self.assertEqual(['p1','p2', '--sub-arg'], args)

    def test_parseError(self):
        self.assertRaises(CmdParseError, self.cmd.parse, ['--not-exist-param'])

    def test_parseWrongType(self):
        self.assertRaises(CmdParseError, self.cmd.parse, ['--num','oi'])

    def test_parseWrongChoice(self):
        self.assertRaises(CmdParseError, self.cmd.parse, ['--choice', 'maybe'])

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
        self.assertEqual('zero', params['foo'])

        # get from env
        os.environ['FOO'] = 'bar'
        self.addCleanup(os.environ.pop, 'FOO', None)
        params2, args2 = cmd.parse([])
        self.assertEqual('bar', params2['foo'])

        # command line has precedence
        params2, args2 = cmd.parse(['--foo', 'XXX'])
        self.assertEqual('XXX', params2['foo'])

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
        self.addCleanup(os.environ.pop, 'FOO', None)
        params, args = cmd.parse([])
        self.assertTrue(params['foo'])

        # get from env
        os.environ['FOO'] = '0'
        params, args = cmd.parse([])
        self.assertFalse(params['foo'])
