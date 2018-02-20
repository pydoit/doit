from io import StringIO
import pytest

from doit.exceptions import InvalidCommand
from doit.cmdparse import CmdOption
from doit.plugin import PluginDict
from doit.task import Task
from doit.cmd_base import Command, TaskLoader, DodoTaskLoader
from doit.cmd_completion import TabCompletion
from doit.cmd_help import Help
from .conftest import CmdFactory

# doesnt test the shell scripts. just test its creation!


class FakeLoader(TaskLoader):
    def load_tasks(self, cmd, params, args):
        task_list = [
            Task("t1", None, ),
            Task("t2", None, task_dep=['t2:a'], has_subtask=True, ),
            Task("t2:a", None, subtask_of='t2'),
            ]
        return task_list, {}


@pytest.fixture
def commands(request):
    sub_cmds = {}
    sub_cmds['tabcompletion'] = TabCompletion
    sub_cmds['help'] = Help
    return PluginDict(sub_cmds)

def test_invalid_shell_option():
    cmd = CmdFactory(TabCompletion)
    pytest.raises(InvalidCommand, cmd.execute,
                  {'shell':'another_shell', 'hardcode_tasks': False}, [])


class TestCmdCompletionBash(object):

    def test_with_dodo__dinamic_tasks(self, commands):
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=DodoTaskLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert 'dodof' in got
        assert 't1' not in got
        assert 'tabcompletion' in got

    def test_no_dodo__hardcoded_tasks(self, commands):
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=FakeLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'bash', 'hardcode_tasks': True}, [])
        got = output.getvalue()
        assert 'dodo.py' not in got
        assert 't1' in got

    def test_cmd_takes_file_args(self, commands):
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=FakeLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert """help)
            COMPREPLY=( $(compgen -W "${tasks} ${sub_cmds}" -- $cur) )
            return 0"""  in got
        assert """tabcompletion)
            COMPREPLY=( $(compgen -f -- $cur) )
            return 0"""  in got


class TestCmdCompletionZsh(object):

    def test_zsh_arg_line(self):
        opt1 = CmdOption({'name':'o1', 'default':'', 'help':'my desc'})
        assert '' == TabCompletion._zsh_arg_line(opt1)

        opt2 = CmdOption({'name':'o2', 'default':'', 'help':'my desc',
                          'short':'s'})
        assert '"-s[my desc]" \\' == TabCompletion._zsh_arg_line(opt2)

        opt3 = CmdOption({'name':'o3', 'default':'', 'help':'my desc',
                          'long':'lll'})
        assert '"--lll[my desc]" \\' == TabCompletion._zsh_arg_line(opt3)

        opt4 = CmdOption({'name':'o4', 'default':'', 'help':'my desc [b]a',
                          'short':'s', 'long':'lll'})
        assert ('"(-s|--lll)"{-s,--lll}"[my desc [b\]a]" \\' ==
                TabCompletion._zsh_arg_line(opt4))

        # escaping `"` test
        opt5 = CmdOption({'name':'o5', 'default':'',
                          'help':'''my "des'c [b]a''',
                          'short':'s', 'long':'lll'})
        assert ('''"(-s|--lll)"{-s,--lll}"[my \\"des'c [b\]a]" \\''' ==
                TabCompletion._zsh_arg_line(opt5))


    def test_cmd_arg_list(self):
        no_args = TabCompletion._zsh_arg_list(Command())
        assert "'*::task:(($tasks))'" not in no_args
        assert "'::cmd:(($commands))'" not in no_args

        class CmdTakeTasks(Command):
            doc_usage = '[TASK ...]'
        with_task_args = TabCompletion._zsh_arg_list(CmdTakeTasks())
        assert "'*::task:(($tasks))'" in with_task_args
        assert "'::cmd:(($commands))'" not in with_task_args

        class CmdTakeCommands(Command):
            doc_usage = '[COMMAND ...]'
        with_cmd_args = TabCompletion._zsh_arg_list(CmdTakeCommands())
        assert "'*::task:(($tasks))'" not in with_cmd_args
        assert "'::cmd:(($commands))'" in with_cmd_args


    def test_cmds_with_params(self, commands):
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=DodoTaskLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'zsh', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert "tabcompletion: generate script" in got

    def test_hardcoded_tasks(self, commands):
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=FakeLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'zsh', 'hardcode_tasks': True}, [])
        got = output.getvalue()
        assert 't1' in got
