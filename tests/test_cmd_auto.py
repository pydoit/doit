import time
from multiprocessing import Process

import pytest

from doit.cmdparse import DefaultUpdate
from doit.task import Task
from doit.cmd_base import TaskLoader
from doit import filewatch
from doit import cmd_auto
from .conftest import CmdFactory


# skip all tests in this module if platform not supported
platform = filewatch.get_platform_system()
pytestmark = pytest.mark.skipif(
    'platform not in filewatch.FileModifyWatcher.supported_platforms')


class TestFindFileDeps(object):
    def find_deps(self, sel_tasks):
        tasks = {
            't1': Task("t1", [""], file_dep=['f1']),
            't2': Task("t2", [""], file_dep=['f2'], task_dep=['t1']),
            't3': Task("t3", [""], file_dep=['f3'], setup=['t1']),
            }
        return cmd_auto.Auto._find_file_deps(tasks, sel_tasks)

    def test_find_file_deps(self):
        assert set(['f1']) == self.find_deps(['t1'])
        assert set(['f1', 'f2']) == self.find_deps(['t2'])
        assert set(['f1', 'f3']) == self.find_deps(['t3'])



class TestDepChanged(object):
    def test_changed(self, dependency1):
        started = time.time()
        assert not cmd_auto.Auto._dep_changed([dependency1], started, [])
        assert cmd_auto.Auto._dep_changed([dependency1], started-100, [])
        assert not cmd_auto.Auto._dep_changed([dependency1], started-100,
                                              [dependency1])


class FakeLoader(TaskLoader):
    def __init__(self, task_list, dep_file):
        self.task_list = task_list
        self.dep_file = dep_file
    def load_tasks(self, cmd, params, args):
        return self.task_list, {'verbosity':2, 'dep_file':self.dep_file}


class TestAuto(object):

    def test_invalid_args(self, dependency1, depfile_name):
        t1 = Task("t1", [""], file_dep=[dependency1])
        task_loader = FakeLoader([t1], depfile_name)
        cmd = CmdFactory(cmd_auto.Auto, task_loader=task_loader)
        # terminates with error number
        assert cmd.parse_execute(['t2']) == 3


    def test_run_callback(self, monkeypatch):
        result = []
        def mock_cmd(callback, shell=None):
            result.append(callback)
        monkeypatch.setattr(cmd_auto, 'call', mock_cmd)

        # success
        result = []
        cmd_auto.Auto._run_callback(0, 'success', 'failure')
        assert 'success' == result[0]

        # failure
        result = []
        cmd_auto.Auto._run_callback(3, 'success', 'failure')
        assert 'failure' == result[0]

        # nothing executed
        result = []
        cmd_auto.Auto._run_callback(0, None , None)
        assert 0 == len(result)
        cmd_auto.Auto._run_callback(1, None , None)
        assert 0 == len(result)




    def test_run_wait(self, dependency1, target1, depfile_name):
        def ok():
            with open(target1, 'w') as fp:
                fp.write('ok')
        t1 = Task("t1", [ok], file_dep=[dependency1])
        cmd = CmdFactory(cmd_auto.Auto,
                         task_loader=FakeLoader([t1], depfile_name))

        run_wait_proc = Process(target=cmd.run_watch,
                                args=(DefaultUpdate(), []))
        run_wait_proc.start()

        # wait until task is executed
        for x in range(5):
            try:
                got = open(target1, 'r').read()
                print(got)
                if got == 'ok':
                    break
            except:
                print('busy')
            time.sleep(0.1)
        else: # pragma: no cover
            raise Exception("target not created")

        # write on file to terminate process
        fd = open(dependency1, 'w')
        fd.write("hi" + str(time.asctime()))
        fd.close()

        run_wait_proc.join(.5)
        if run_wait_proc.is_alive(): # pragma: no cover
            # this test is very flaky so we give it one more chance...
            # write on file to terminate process
            fd = open(dependency1, 'w')
            fd.write("hi" + str(time.asctime()))
            fd.close()

            run_wait_proc.join(1)
            if run_wait_proc.is_alive(): # pragma: no cover
                run_wait_proc.terminate()
                raise Exception("process not terminated")
        assert 0 == run_wait_proc.exitcode


    def test_execute(self, monkeypatch):
        # use dumb operation instead of executing RUN command and waiting event
        def fake_run(self, params, args): # pragma: no cover
            5 + 2
        monkeypatch.setattr(cmd_auto.Auto, 'run_watch', fake_run)

        # after join raise exception to stop AUTO command
        original = cmd_auto.Process.join
        def join_interrupt(self):
            original(self)
            raise KeyboardInterrupt()
        monkeypatch.setattr(cmd_auto.Process, 'join', join_interrupt)

        cmd = CmdFactory(cmd_auto.Auto)
        cmd.execute(None, None)
