from six import StringIO
import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_clean import Clean


class TestCmdClean(object):

    @pytest.fixture
    def tasks(self, request):
        self.cleaned = []
        def myclean(name):
            self.cleaned.append(name)
        return [
            Task("t1", None, task_dep=['t2'], clean=[(myclean,('t1',))]),
            Task("t2", None, clean=[(myclean,('t2',))]),
            Task("t3", None, task_dep=['t3:a'], has_subtask=True,
                 clean=[(myclean,('t3',))]),
            Task("t3:a", None, clean=[(myclean,('t3:a',))], is_subtask=True),
            Task("t4", None, task_dep=['t1'], clean=[(myclean,('t4',))] ),
            ]

    def test_clean_all(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, False, True)
        assert ['t1','t2', 't3:a', 't3', 't4'] == self.cleaned

    def test_clean_default(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks,
                          config={'default_tasks':['t1']})
        cmd_clean._execute(False, False, False)
        # default enable --clean-dep by default
        assert ['t2', 't1'] == self.cleaned

    def test_clean_default_all(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, False, False)
        # default enable --clean-dep by default
        assert set(['t1','t2', 't3:a', 't3', 't4']) == set(self.cleaned)

    def test_clean_selected(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks,
                          config={'default_tasks':['t1']})
        cmd_clean._execute(False, False, False, ['t2'])
        assert ['t2'] == self.cleaned

    def test_clean_taskdep(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, True, False, ['t1'])
        assert ['t2', 't1'] == self.cleaned

    def test_clean_taskdep_recursive(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, True, False, ['t4'])
        assert ['t2', 't1', 't4'] == self.cleaned

    def test_clean_subtasks(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, False, False, ['t3'])
        assert ['t3:a', 't3'] == self.cleaned

    def test_clean_taskdep_once(self, tasks):
        # do not execute clean operation more than once
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks)
        cmd_clean._execute(False, True, False, ['t1', 't2'])
        assert ['t2', 't1'] == self.cleaned

    def test_clean_invalid_task(self, tasks):
        output = StringIO()
        cmd_clean = Clean(outstream=output, task_list=tasks,
                          config={'default_tasks':['t1']})
        pytest.raises(InvalidCommand, cmd_clean._execute,
                      False, False, False, ['xxxx'])
