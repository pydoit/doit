from StringIO import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_list import List
from tests.conftest import tasks_sample


class TestCmdList(object):

    def testDefault(self, depfile):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in tasks if not t.is_subtask]
        assert sorted(expected) == got

    def testDoc(self, depfile):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks)
        cmd_list._execute(quiet=False)
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
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=[my_task])
        cmd_list._execute(list_deps=True)
        got = output.getvalue()
        assert "d2.txt" in got

    def testSubTask(self, depfile):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks)
        cmd_list._execute(subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in sorted(tasks)]
        assert expected == got

    def testFilter(self, depfile):
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1', 't2'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testFilterSubtask(self, depfile):
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1.a'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1.a']
        assert expected == got

    def testFilterAll(self, depfile):
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks_sample())
        cmd_list._execute(subtasks=True, pos_args=['g1'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self, depfile):
        task_list = tasks_sample()
        depfile.ignore(task_list[0]) # t1
        depfile.save_success(task_list[1]) # t2
        depfile.close()

        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=task_list)
        cmd_list._execute(status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        assert 'R g1' in got
        assert 'I t1' in got
        assert 'U t2' in got

    def testNoPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=task_list)
        cmd_list._execute(pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = []
        assert expected == got

    def testWithPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=task_list)
        cmd_list._execute(private=True, pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['_s3']
        assert expected == got

    def testListInvalidTask(self, depfile):
        output = StringIO()
        cmd_list = List(outstream=output, dep_file=depfile.name,
                        task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_list._execute, pos_args=['xxx'])
