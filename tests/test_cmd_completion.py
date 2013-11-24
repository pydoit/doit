from six import StringIO
import pytest

from doit.exceptions import InvalidCommand
from doit.cmdparse import CmdOption
from doit.task import Task
from doit.cmd_base import Command, TaskLoader, DodoTaskLoader
from doit.cmd_completion import TabCompletion
from doit.doit_cmd import DoitMain

# doesnt test the shell scripts. just test its creation!


class FakeLoader(TaskLoader):
    def load_tasks(self, cmd, params, args):
        task_list = [
            Task("t1", None, ),
            Task("t2", None, task_dep=['t2:a'], has_subtask=True, ),
            Task("t2:a", None, is_subtask=True),
            ]
        return task_list, {}


@pytest.fixture
def doit_app(request):
    app = DoitMain()
    app.sub_cmds['tabcompletion'] = TabCompletion()
    return app

def test_invalid_shell_option(doit_app):
    cmd = TabCompletion()
    pytest.raises(InvalidCommand, cmd.execute,
                  {'shell':'another_shell', 'hardcode_tasks': False}, [])


class TestCmdCompletionBash(object):

    def test_with_dodo__dinamic_tasks(self, doit_app):
        output = StringIO()
        cmd = TabCompletion(task_loader=DodoTaskLoader(), outstream=output)
        cmd.doit_app = doit_app
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert 'dodof' in got
        assert 't1' not in got
        assert 'tabcompletion' in got

    def test_no_dodo__hardcoded_tasks(self, doit_app):
        output = StringIO()
        cmd = TabCompletion(task_loader=FakeLoader(), outstream=output)
        cmd.doit_app = doit_app
        cmd.execute({'shell':'bash', 'hardcode_tasks': True}, [])
        got = output.getvalue()
        assert 'dodo.py' not in got
        assert 't1' in got


class TestCmdCompletionZsh(object):

    def test_zsh_arg_line(self):
        opt1 = CmdOption({'name':'o1', 'default':'', 'help':'my desc'})
        assert '' == TabCompletion._zsh_arg_line(opt1)

        opt2 = CmdOption({'name':'o2', 'default':'', 'help':'my desc',
                          'short':'s'})
        assert "'-s[my desc]' \\" == TabCompletion._zsh_arg_line(opt2)

        opt3 = CmdOption({'name':'o3', 'default':'', 'help':'my desc',
                          'long':'lll'})
        assert "'--lll[my desc]' \\" == TabCompletion._zsh_arg_line(opt3)

        opt4 = CmdOption({'name':'o4', 'default':'', 'help':'my desc [b]a',
                          'short':'s', 'long':'lll'})
        assert ("'(-s|--lll)'{-s,--lll}'[my desc [b\]a]' \\" ==
                TabCompletion._zsh_arg_line(opt4))


    def test_cmd_arg_list(self, doit_app):
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


    def test_cmds_with_params(self, doit_app):
        output = StringIO()
        cmd = TabCompletion(task_loader=DodoTaskLoader(), outstream=output)
        cmd.doit_app = doit_app
        cmd.execute({'shell':'zsh', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert "tabcompletion: generate script" in got

    def test_hardcoded_tasks(self, doit_app):
        output = StringIO()
        cmd = TabCompletion(task_loader=FakeLoader(), outstream=output)
        cmd.doit_app = doit_app
        cmd.execute({'shell':'zsh', 'hardcode_tasks': True}, [])
        got = output.getvalue()
        assert 't1' in got
