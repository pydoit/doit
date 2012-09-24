import pytest

from doit.cmdparse import CmdParseError, CmdOption
from doit.doit_cmd import Command


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



class SampleCmd(Command):
    doc_purpose = 'PURPOSE'
    doc_usage = 'USAGE'
    doc_description = 'DESCRIPTION'

    @staticmethod
    def execute(params, args):
        return params, args

    def set_options(self):
        options = [opt_bool, opt_rare, opt_int, opt_no]
        return [CmdOption(o) for o in options]

class TestCommand(object):

    def pytest_funcarg__cmd(self, request):
        def create_sample_cmd():
            return SampleCmd()
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
        assert opt_no['name'] in [o.name for o in cmd.options]
        assert 'user cant modify me' not in text


    def test_call(self, cmd):
        params, args = cmd.parse_execute(['-n','7','ppp'])
        assert ['ppp'] == args
        assert 7 == params['num']

    def test_failCall(self, cmd):
        pytest.raises(CmdParseError, cmd.parse_execute, ['-x','35'])
