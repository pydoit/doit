import StringIO

from doit.task import Task
from doit.cmd_list import List
from tests.conftest import tasks_sample


class TestCmdList(object):

    def testDefault(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmd_list = List(dep_file=depfile.name, task_list=tasks, sel_tasks=[])
        cmd_list._execute(output)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in tasks if not t.is_subtask]
        assert sorted(expected) == got

    def testDoc(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmd_list = List(dep_file=depfile.name, task_list=tasks, sel_tasks=[])
        cmd_list._execute(output, print_doc=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        for t in sorted(tasks):
            if not t.is_subtask:
                expected.append([t.name, t.doc])
        assert len(expected) == len(got)
        for exp1, got1 in zip(expected, got):
            assert exp1 == got1.split(None, 1)

    def testDependencies(self, depfile):
        my_task = Task("t2", [""], file_dep=['d2.txt'])
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=[my_task], sel_tasks=[])
        cmd_list._execute(output, print_dependencies=True)
        got = output.getvalue()
        assert "d2.txt" in got

    def testSubTask(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmd_list = List(dep_file=depfile.name, task_list=tasks, sel_tasks=[])
        cmd_list._execute(output, print_subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in sorted(tasks)]
        assert expected == got

    def testFilter(self, depfile):
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=tasks_sample(),
                        sel_tasks=['g1', 't2'])
        cmd_list._execute(output)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testFilterSubtask(self, depfile):
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=tasks_sample(),
                        sel_tasks=['g1.a'])
        cmd_list._execute(output)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1.a']
        assert expected == got

    def testFilterAll(self, depfile):
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=tasks_sample(),
                        sel_tasks=['g1'])
        cmd_list._execute(output, print_subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self, depfile):
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=tasks_sample(),
                        sel_tasks=['g1'])
        cmd_list._execute(output, print_status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['R g1']
        assert expected == got

    def testNoPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=task_list,
                        sel_tasks=['_s3'])
        cmd_list._execute(output)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = []
        assert expected == got

    def testWithPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmd_list = List(dep_file=depfile.name, task_list=task_list,
                        sel_tasks=['_s3'])
        cmd_list._execute(output, print_private=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['_s3']
        assert expected == got


