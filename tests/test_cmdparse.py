import pickle

import pytest

from doit import cmdparse


class TestDefaultUpdate(object):
    def test(self):
        du = cmdparse.DefaultUpdate()

        du.set_default('a', 0)
        du.set_default('b', 0)

        assert 0 == du['a']
        assert 0 == du['b']

        du['b'] = 1
        du.update_defaults({'a':2, 'b':2})
        assert 2 == du['a']
        assert 1 == du['b']

    # http://bugs.python.org/issue826897
    def test_pickle(self):
        du = cmdparse.DefaultUpdate()
        du.set_default('x', 0)
        dump = pickle.dumps(du,2)
        pickle.loads(dump)


opt_bool = {'name': 'flag',
            'short':'f',
            'long': 'flag',
            'inverse':'no-flag',
            'type': bool,
            'default': False,
            'help': 'help for opt1'}

opt_rare = {'name': 'rare',
            'long': 'rare-bool',
            'type': bool,
            'default': False,
            'help': 'help for opt2'}

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

def cmd_xxx(params, args):
    return params, args

class TestCommandInit(object):

    def test_non_required_fields(self):
        opt1 = {'name':'op1', 'default':''}
        cmd = cmdparse.Command('xxx', [opt1], None, None)
        assert 'long' in cmd.options[0]

    def test_invalid_field(self):
        opt1 = {'name':'op1', 'default':'', 'non_existent':''}
        pytest.raises(cmdparse.CmdParseError,
                       cmdparse.Command, 'xxx', [opt1], None, None)

    def test_missing_field(self):
        opt1 = {'name':'op1', 'long':'abc'}
        pytest.raises(cmdparse.CmdParseError,
                       cmdparse.Command, 'xxx', [opt1], None, None)



class TestCommand(object):

    def pytest_funcarg__cmd(self, request):
        def create_sample_cmd():
            options = [opt_bool, opt_rare, opt_int, opt_no]
            doc = {'purpose':'PURPOSE','usage':'USAGE',
                   'description':'DESCRIPTION'}
            cmd = cmdparse.Command('xxx', options, cmd_xxx, doc)
            return cmd
        return request.cached_setup(
            setup=create_sample_cmd,
            scope="function")


    def test_help(self, cmd):
        text = cmd.help()
        assert 'PURPOSE' in text
        assert 'USAGE' in text
        assert 'DESCRIPTION' in text
        assert '-f' in text
        assert '--rare-bool' in text
        assert 'help for opt1' in text
        assert opt_no['name'] in [o['name'] for o in cmd.options]
        assert 'user cant modify me' not in text

    def test_short(self, cmd):
        assert "fn:" == cmd.get_short(), cmd.get_short()

    def test_long(self, cmd):
        assert ["flag", "no-flag", "rare-bool", "number="] == cmd.get_long()

    def test_getOption(self, cmd):
        # short
        opt, inverse = cmd.get_option('-f')
        assert (opt_bool['name'], False) == (opt['name'], inverse)
        # long
        opt, inverse = cmd.get_option('--rare-bool')
        assert (opt_rare['name'], False) == (opt['name'], inverse)
        # inverse
        opt, inverse = cmd.get_option('--no-flag')
        assert (opt_bool['name'], True) == (opt['name'], inverse)
        # not found
        opt, inverse = cmd.get_option('not-there')
        assert (None, None) == (opt, inverse)


    def test_parseDefaults(self, cmd):
        params, args = cmd.parse([])
        assert False == params['flag']
        assert 5 == params['num']

    def test_parseShortValues(self, cmd):
        params, args = cmd.parse(['-n','89','-f'])
        assert True == params['flag']
        assert 89 == params['num']

    def test_parseLongValues(self, cmd):
        params, args = cmd.parse(['--rare-bool','--num','89', '--no-flag'])
        assert True == params['rare']
        assert False == params['flag']
        assert 89 == params['num']

    def test_parsePositionalArgs(self, cmd):
        params, args = cmd.parse(['-f','p1','p2','--sub-arg'])
        assert ['p1','p2','--sub-arg'] == args

    def test_parseExtraParams(self, cmd):
        params, args = cmd.parse([], new_param='ho')
        assert "ho" == params['new_param']

    def test_parseWrongType(self, cmd):
        pytest.raises(cmdparse.CmdParseError, cmd.parse, ['--num','oi'])

    def test_call(self, cmd):
        params, args = cmd(['-n','7','ppp'])
        assert ['ppp'] == args
        assert 7 == params['num']

    def test_failCall(self, cmd):
        pytest.raises(cmdparse.CmdParseError, cmd,['-x','35'])
