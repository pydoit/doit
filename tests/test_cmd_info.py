import six
from six import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_info import Info
from doit.dependency import MD5Checker, TimestampChecker
from .conftest import CmdFactory, get_abspath

class TestCmdInfo(object):

    def test_info(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=depfile.name, task_list=[task])
        cmd._execute(['t1'])
        assert """name:'t1'""" in output.getvalue()
        assert """'tests/data/dependency1'""" in output.getvalue()

    def test_info_status_uptodate(self, depfile):
        output = StringIO()
        task = Task("t1", [], uptodate=[True])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        assert """Is up to date.""" in output.getvalue()

    def test_info_status_nodeps(self, depfile):
        output = StringIO()
        task = Task("t1", [])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        assert """Is not up to date:""" in output.getvalue()
        assert """The task has no dependencies.""" in output.getvalue()

    def test_info_status_notuptodate(self, depfile):
        filePath = get_abspath("data/dependency2")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        output = StringIO()
        task = Task("t1", [], targets=['tests/data/target1'], file_dep=['tests/data/dependency1', 'tests/data/dependency2'], uptodate=[False])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        assert """Is not up to date:""" in output.getvalue()
        assert """The following uptodate objects evaluate to false:""" in output.getvalue()
        assert """- False (args=None, kwargs=None)""" in output.getvalue()
        assert """The following file dependencies are missing:""" in output.getvalue()
        assert """- tests/data/dependency1""" in output.getvalue()
        assert """The following file dependencies have changed:""" in output.getvalue()
        assert """- tests/data/dependency2""" in output.getvalue()
        assert """The following targets do not exist:""" in output.getvalue()
        assert """- tests/data/target1""" in output.getvalue()

    def test_info_status_change_filedep(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency2'])
        depfile.get_status(task, {})
        depfile.save_success(task)
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        print(output.getvalue())
        assert """Is not up to date:""" in output.getvalue()
        assert """The following file dependencies were added:""" in output.getvalue()
        assert """- tests/data/dependency1""" in output.getvalue()
        assert """The following file dependencies were removed:""" in output.getvalue()
        assert """- tests/data/dependency2""" in output.getvalue()

    def test_info_status_change_checker(self, depfile):
        filePath = get_abspath("data/dependency2")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()

        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency2'])
        depfile.checker = TimestampChecker()
        depfile.save_success(task)
        depfile.checker = MD5Checker()
        task = Task("t1", [], file_dep=['tests/data/dependency2'])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        print(output.getvalue())
        assert """Is not up to date:""" in output.getvalue()
        assert """The file_dep checker changed from TimestampChecker to MD5Checker.""" in output.getvalue()

    def test_info_unicode(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=[six.u('tests/data/dependency1')])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=depfile.name, task_list=[task])
        cmd._execute(['t1'])
        assert """name:'t1'""" in output.getvalue()
        assert """'tests/data/dependency1'""" in output.getvalue()

    def test_invalid_command_args(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=depfile.name, task_list=[task])
        # fails if number of args != 1
        pytest.raises(InvalidCommand, cmd._execute, [])
        pytest.raises(InvalidCommand, cmd._execute, ['t1', 't2'])


