import os.path
from six import StringIO

import mock

from doit.cmdparse import DefaultUpdate
from doit.task import Task
from doit.cmd_strace import Strace


class TestCmdRun(object):

    def test_dep(self, dependency1, depfile_name):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        params = DefaultUpdate(dep_file=depfile_name, show_all=False,
                               keep_trace=False, backend='dbm')
        result = cmd.execute(params, ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")
        dep_path = os.path.abspath("tests/data/dependency1")
        assert "R %s" % dep_path in got[0]


    def test_opt_show_all(self, dependency1, depfile_name):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        params = DefaultUpdate(dep_file=depfile_name, show_all=True,
                               keep_trace=False, backend='dbm')
        result = cmd.execute(params, ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")
        assert "cat" in got[0]

    def test_opt_keep_trace(self, dependency1, depfile_name):
        output = StringIO()
        task = Task("tt", ["cat %(dependencies)s"],
                    file_dep=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        params = DefaultUpdate(dep_file=depfile_name, show_all=True,
                               keep_trace=True, backend='dbm')
        result = cmd.execute(params, ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")
        assert "cat" in got[0]
        assert os.path.exists(cmd.TRACE_OUT)
        os.unlink(cmd.TRACE_OUT)


    def test_target(self, dependency1, depfile_name):
        output = StringIO()
        task = Task("tt", ["touch %(targets)s"],
                    targets=['tests/data/dependency1'])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        params = DefaultUpdate(dep_file=depfile_name, show_all=False,
                               keep_trace=False, backend='dbm')
        result = cmd.execute(params, ['tt'])
        assert 0 == result
        got = output.getvalue().split("\n")
        tgt_path = os.path.abspath("tests/data/dependency1")
        assert "W %s" % tgt_path in got[0]

    def test_ignore_python_actions(self, dependency1, depfile_name):
        output = StringIO()
        def py_open():
            with open(dependency1) as ignore:
                ignore
        task = Task("tt", [py_open])
        cmd = Strace(outstream=output)
        cmd._loader.load_tasks = mock.Mock(return_value=([task], {}))
        params = DefaultUpdate(dep_file=depfile_name, show_all=False,
                               keep_trace=False, backend='dbm')
        result = cmd.execute(params, ['tt'])
        assert 0 == result

