import six
from six import StringIO

import pytest

from doit.exceptions import InvalidCommand
from doit.task import Task
from doit.cmd_info import Info
from .conftest import CmdFactory

class TestCmdInfo(object):

    def test_info(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         dep_file=depfile.name, task_list=[task])
        cmd._execute(['t1'])
        assert """name:'t1'""" in output.getvalue()
        assert """'tests/data/dependency1'""" in output.getvalue()

    def test_info_status(self, depfile):
        output = StringIO()
        task = Task("t1", [], file_dep=['tests/data/dependency1'])
        cmd = CmdFactory(Info, outstream=output,
                         task_list=[task], dep_manager=depfile)
        cmd._execute(['t1'], show_execute_status=True)
        assert """name:'t1'""" in output.getvalue()
        assert """'tests/data/dependency1'""" in output.getvalue()
        assert """Is not up to date:""" in output.getvalue()
        assert ("""The following file dependencies have changed:""" in output.getvalue()
             or """The following file dependencies are missing:""" in output.getvalue())
        assert """- tests/data/dependency1""" in output.getvalue()

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


