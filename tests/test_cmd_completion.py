from six import StringIO

from doit.task import Task
from doit.cmd_base import TaskLoader, DodoTaskLoader
from doit.cmd_completion import TabCompletion
from doit.doit_cmd import DoitMain



class FakeLoader(TaskLoader):
    def load_tasks(self, cmd, params, args):
        task_list = [
            Task("t1", None, ),
            Task("t2", None, task_dep=['t2:a'], has_subtask=True, ),
            Task("t2:a", None, is_subtask=True),
            ]
        return task_list, {}

class TestCmdCompletion(object):
    # doesnt test the shell script. just test its creation!

    def test_with_dodo__dinamic_tasks(self):
        output = StringIO()
        cmd = TabCompletion(task_loader=DodoTaskLoader(), outstream=output)
        cmd.doit_app = DoitMain()
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        assert 'dodof' in got
        assert 't1' not in got

    def test_no_dodo__hardcoded_tasks(self):
        output = StringIO()
        cmd = TabCompletion(task_loader=FakeLoader(), outstream=output)
        cmd.doit_app = DoitMain()
        cmd.execute({'shell':'bash', 'hardcode_tasks': True}, [])
        got = output.getvalue()
        assert 'dodo.py' not in got
        assert 't1' in got
