import time
from StringIO import StringIO
from multiprocessing import Process

from doit.cmdparse import DefaultUpdate
from doit.task import Task
from doit.cmd_base import TaskLoader
from doit.cmd_auto import Auto


class FakeLoader(TaskLoader):
    def __init__(self, task_list):
        self.task_list = task_list
    def load_tasks(self, cmd, params, args):
        return self.task_list, {}


class TestAuto(object):
    def testProcessRun(self, dependency1, depfile, capsys):
        output = StringIO()
        t1 = Task("t1", [""], file_dep=[dependency1])
        cmd_run = Auto(task_loader=FakeLoader([t1]),
                       dep_file=depfile.name,
                       outstream=output)

        run_wait_proc = Process(target=cmd_run.run_watch,
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

