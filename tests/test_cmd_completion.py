from six import StringIO
import pytest

from doit.cmdparse import CmdOption
from doit.task import Task
from doit.cmd_base import TaskLoader, DodoTaskLoader
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


    def test_cmds_with_params(self, doit_app):
        output = StringIO()
        cmd = TabCompletion(task_loader=DodoTaskLoader(), outstream=output)
        cmd.doit_app = doit_app
        cmd.execute({'shell':'zsh', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert "tabcompletion: generate script" in got
