import StringIO

from doit.task import Task
from doit.cmd_clean import Clean
doit_clean = Clean._execute

class TestCmdClean(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            self.cleaned = []
            def myclean(name):
                self.cleaned.append(name)
            self.tasks = [
                Task("t1", None, task_dep=['t2'], clean=[(myclean,('t1',))]),
                Task("t2", None, clean=[(myclean,('t2',))]),
                Task("t3", None, task_dep=['t3:a'], has_subtask=True,
                     clean=[(myclean,('t3',))]),
                Task("t3:a", None, clean=[(myclean,('t3:a',))]),
                ]
        return request.cached_setup(
            setup=create_tasks,
            scope="function")

    def test_clean_all(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, False, True, 'xxx', 'xxx')
        assert ['t1','t2', 't3:a', 't3'] == self.cleaned

    def test_clean_default(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, False, False, ['t1'], [])
        # default enable --clean-dep by default
        assert ['t2', 't1'] == self.cleaned

    def test_clean_selected(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, False, False, 'xxx', ['t2'])
        assert ['t2'] == self.cleaned

    def test_clean_taskdep(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, True, False, 'xxx', ['t1'])
        assert ['t2', 't1'] == self.cleaned

    def test_clean_subtasks(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, False, False, 'xxx', ['t3'])
        assert ['t3:a', 't3'] == self.cleaned

    def test_clean_taskdep_once(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, False, True, False, 'xxx', ['t1', 't2'])
        assert ['t2', 't1'] == self.cleaned


