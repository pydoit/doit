from StringIO import StringIO
import os.path

import mock

from doit.cmdparse import DefaultUpdate
from doit.task import Task
from doit.cmd_strace import Strace


class TestCmdRun(object):

    def test_dep(self, dependency1, depfile):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        result = cmd.execute(DefaultUpdate(dep_file=depfile.name), ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        dep_path = os.path.abspath("tests/data/dependency1")
        assert "D %s" % dep_path in got


    def test_target(self, dependency1, depfile):
        output = StringIO()
        task = Task("tt", ["touch %(targets)s"],
                    targets=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        result = cmd.execute(DefaultUpdate(dep_file=depfile.name), ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        tgt_path = os.path.abspath("tests/data/dependency1")
        assert "T %s" % tgt_path in got
