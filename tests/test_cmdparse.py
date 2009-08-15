import getopt
import nose

from doit import cmdparse

opt_bool = {'name': 'flag',
            'short':'f',
            'long': '',
            'type': bool,
            'default': False,
            'help': 'help for opt1'}

opt_rare = {'name': 'rare',
            'short':'',
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


class TestCommand(object):

    def setUp(self):
        options = [opt_bool, opt_rare, opt_int, opt_no]
        doc = {'purpose':'PURPOSE','usage':'USAGE','description':'DESCRIPTION'}
        self.cmd = cmdparse.Command('xxx', options, cmd_xxx, doc)

    def test_help(self):
        text = self.cmd.help()
        assert 'PURPOSE' in text
        assert 'USAGE' in text
        assert 'DESCRIPTION' in text
        assert '-f' in text
        assert '--rare-bool' in text
        assert 'help for opt1' in text
        assert opt_no in self.cmd.options
        assert 'user cant modify me' not in text

    def test_short(self):
        assert "fn:" == self.cmd.get_short(), self.cmd.get_short()

    def test_long(self):
        assert ["rare-bool", "number="] == self.cmd.get_long()

    def test_getOption(self):
        assert opt_bool == self.cmd.get_option('-f')
        assert opt_rare == self.cmd.get_option('--rare-bool')
        assert opt_int == self.cmd.get_option('-n')
        assert opt_int == self.cmd.get_option('--number')
        assert None == self.cmd.get_option('not-there')


    def test_parseDefaults(self):
        params, args = self.cmd.parse([])
        assert False == params['flag']
        assert 5 == params['num']

    def test_parseShortValues(self):
        params, args = self.cmd.parse(['-n','89','-f'])
        assert True == params['flag']
        assert 89 == params['num']

    def test_parseLongValues(self):
        params, args = self.cmd.parse(['--rare-bool','--num','89'])
        assert True == params['rare']
        assert 89 == params['num']

    def test_parsePositionalArgs(self):
        params, args = self.cmd.parse(['-f','p1','p2','--sub-arg'])
        assert ['p1','p2','--sub-arg'] == args

    def test_parseExtraParams(self):
        params, args = self.cmd.parse([], new_param='ho')
        assert "ho" == params['new_param']

    def test_call(self):
        params, args = self.cmd(['-n','7','ppp'])
        assert ['ppp'] == args
        assert 7 == params['num']

    def test_failCall(self):
        nose.tools.assert_raises(getopt.GetoptError, self.cmd,['-x','35'])
