import time
from StringIO import StringIO
from multiprocessing import Process

from doit.cmdparse import DefaultUpdate
from doit.task import Task
from doit.cmd_base import TaskLoader
from doit import cmd_auto


class FakeLoader(TaskLoader):
    def __init__(self, task_list):
        self.task_list = task_list
    def load_tasks(self, cmd, params, args):
        return self.task_list, {}


class TestAuto(object):
    def test_run_wait(self, dependency1, depfile, capsys):
        output = StringIO()
        t1 = Task("t1", [""], file_dep=[dependency1])
        cmd = cmd_auto.Auto(task_loader=FakeLoader([t1]),
                       dep_file=depfile.name,
                       outstream=output)

        run_wait_proc = Process(target=cmd.run_watch,
                                args=(DefaultUpdate(), []))
        run_wait_proc.start()

        # wait for task to run
        time.sleep(.5)

        # write on file to terminate process
        fd = open(dependency1, 'w')
        fd.write("hi" + str(time.asctime()))
        fd.close()

        run_wait_proc.join(1)
        if run_wait_proc.is_alive(): # pragma: no cover
            run_wait_proc.terminate()
            raise Exception("process not terminated")

    def test_execute(self, monkeypatch):
        # use dumb operation instead of executing RUN command and waiting event
        def fake_run(self, params, args):
            5 + 2
        monkeypatch.setattr(cmd_auto.Auto, 'run_watch', fake_run)

        # after join raise exception to stop AUTO command
        original = cmd_auto.Process.join
        def join_interrupt(self):
            original(self)
            raise KeyboardInterrupt()
        monkeypatch.setattr(cmd_auto.Process, 'join', join_interrupt)

        cmd = cmd_auto.Auto()
        cmd.execute(None, None)


