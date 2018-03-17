from io import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.tools import result_dep
from doit.cmd_list import List
from tests.conftest import tasks_sample, tasks_bad_sample, CmdFactory


class TestCmdList(object):

    def testQuiet(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in tasks if not t.subtask_of]
        assert sorted(expected) == got

    def testDoc(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(quiet=False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        for t in sorted(tasks):
            if not t.subtask_of:
                expected.append([t.name, t.doc])
        assert len(expected) == len(got)
        for exp1, got1 in zip(expected, got):
            assert exp1 == got1.split(None, 1)

    def testCustomTemplate(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(template='xxx {name} xxx {doc}')
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        assert 'xxx g1 xxx g1 doc string' == got[0]
        assert 'xxx t3 xxx t3 doc string' == got[3]

    def testDependencies(self):
        my_task = Task("t2", [""], file_dep=['d2.txt'])
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=[my_task])
        cmd_list._execute(list_deps=True)
        got = output.getvalue()
        assert "d2.txt" in got

    def testSubTask(self):
        output = StringIO()
        tasks = tasks_sample()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks)
        cmd_list._execute(subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in sorted(tasks)]
        assert expected == got

    def testFilter(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1', 't2'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testFilterSubtask(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(pos_args=['g1.a'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1.a']
        assert expected == got

    def testFilterAll(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        cmd_list._execute(subtasks=True, pos_args=['g1'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self, dependency1, dep_manager):
        task_list = tasks_sample()
        dep_manager.ignore(task_list[0]) # t1
        dep_manager.save_success(task_list[1]) # t2
        dep_manager.close()

        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=dep_manager.name,
                        backend='dbm', task_list=task_list)
        cmd_list._execute(status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        assert 'R g1' in got
        assert 'I t1' in got
        assert 'U t2' in got


    def testErrorStatus(self, dependency1, dep_manager):
        """Check that problematic tasks show an 'E' as status."""
        task_list = tasks_bad_sample()

        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_manager=dep_manager,
                              task_list=task_list)
        cmd_list._execute(status=True)
        for line in output.getvalue().split('\n'):
            if line:
                assert line.strip().startswith('E ')


    def testStatus_result_dep_bug_gh44(self, dependency1, dep_manager):
        # make sure task dict is passed when checking up-to-date
        task_list = [Task("t1", [""], doc="t1 doc string"),
                     Task("t2", [""], uptodate=[result_dep('t1')]),]

        dep_manager.save_success(task_list[0]) # t1
        dep_manager.close()

        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=dep_manager.name,
                              backend='dbm', task_list=task_list)
        cmd_list._execute(status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        assert 'R t1' in got
        assert 'R t2' in got

    def testNoPrivate(self):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute(pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = []
        assert expected == got

    def testWithPrivate(self):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=task_list)
        cmd_list._execute(private=True, pos_args=['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['_s3']
        assert expected == got

    def testListInvalidTask(self):
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, task_list=tasks_sample())
        pytest.raises(InvalidCommand, cmd_list._execute, pos_args=['xxx'])


    def test_unicode_name(self, dep_manager):
        task_list = [Task("t做", [""], doc="t1 doc string 做"),]
        output = StringIO()
        cmd_list = CmdFactory(List, outstream=output, dep_file=dep_manager.name,
                              task_list=task_list)
        cmd_list._execute()
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        assert 't做' == got[0]
