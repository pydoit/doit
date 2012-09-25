import threading
import time

from doit.task import Task
from doit.cmd_auto import _auto_watch, FileModifyWatcher, Auto
from tests.test_runner import FakeReporter
from tests.conftest import remove_db


class TestCmdAuto(object):

    def test_watch(self, cwd, depfile):
        t1 = Task("t1", None, file_dep=["f1"])
        t2 = Task("t2", None, file_dep=["f2"], calc_dep=["t1"])
        # simple task
        w1_tasks, w1_files = _auto_watch([t1, t2], ["t1"])
        assert ["t1"] == w1_tasks
        assert ["f1"] == w1_files
        # with calc_dep
        w2_tasks, w2_files = _auto_watch([t1, t2], ["t2"])
        assert sorted(["t1", "t2"]) == sorted(w2_tasks)
        assert ["f1", "f2"] == w2_files


    def test(self, cwd, monkeypatch, depfile):
        file1, file2, file3 = 'data/w1.txt', 'data/w2.txt', 'data/w3.txt'
        stop_file = 'data/stop'
        should_stop = []
        started = []
        # attach file watcher "stop" loop stuff
        def _handle(self, event):
            if event.pathname in self.file_list:
                self.handle_event(event)
                if event.pathname.endswith("stop"):
                    should_stop.append(True)
        monkeypatch.setattr(FileModifyWatcher, "_handle", _handle)
        from doit import dependency
        monkeypatch.setattr(dependency, "USE_FILE_TIMESTAMP", False)

        # stop file watcher
        def loop_callback(notifier):
            started.append(True)
            if should_stop:
                raise KeyboardInterrupt

        remove_db(depfile.name)
        # create files
        for fx in (file1, file2, file3, stop_file):
            fd = open(fx, 'w')
            fd.write("hi")
            fd.close()
        #
        def hi():
            print "hello"
        t1 = Task("t1", [(hi,)], [file1])
        t2 = Task("t2", [(hi,)], [file2])
        tstop = Task("stop", [(hi,)],  [stop_file])
        task_list = [t1, t2, tstop]
        reporter = FakeReporter()
        run_args = (None, reporter, loop_callback)
        cmd = Auto(dep_file=depfile.name, task_list=task_list,
                   sel_tasks=["t1", "t2", "stop"])
        loop_thread = threading.Thread(target=cmd._execute, args=run_args)
        loop_thread.daemon = True
        loop_thread.start()

        # wait watcher to be ready
        while not started: assert loop_thread.isAlive()
        # write in watched file ====expected=====> .  t1
        fd = open(file1, 'w')
        fd.write("mod1")
        fd.close()
        # write in non-watched file ============> None
        fd = open(file3, 'w')
        fd.write("mod2")
        fd.close()

        sleep_factor = 0.4 # ensure execution is over before start a new one
        time.sleep(sleep_factor)
        # write in another watched file ========> .  t2
        fd = open(file2, 'w')
        fd.write("mod3")
        fd.close()

        time.sleep(sleep_factor)
        # write in watched file ====expected=====> .  t1
        fd = open(file1, 'w')
        fd.write("mod4")
        fd.close()

        time.sleep(sleep_factor)
        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("mod5")
        fd.close()
        loop_thread.join(10)
        assert not loop_thread.isAlive()

        # tasks are executed once when auto starts
        assert ('start', t1) == reporter.log[0]
        assert ('execute', t1) == reporter.log[1]
        assert ('success', t1) == reporter.log[2]
        assert ('start', t2) == reporter.log[3]
        assert ('execute', t2) == reporter.log[4]
        assert ('success', t2) == reporter.log[5]
        assert ('start', tstop) == reporter.log[6]
        assert ('execute', tstop) == reporter.log[7]
        assert ('success', tstop) == reporter.log[8]
        # modify t1
        assert ('start', t1) == reporter.log[9]
        assert ('execute', t1) == reporter.log[10]
        assert ('success', t1) == reporter.log[11]
        assert ('start', t2) == reporter.log[12]
        assert ('up-to-date', t2) == reporter.log[13]
        assert ('start', tstop) == reporter.log[14]
        assert ('up-to-date', tstop) == reporter.log[15]
        # modify t2
        assert ('start', t1) == reporter.log[16]
        assert ('up-to-date', t1) == reporter.log[17]
        assert ('start', t2) == reporter.log[18]
        assert ('execute', t2) == reporter.log[19]
        assert ('success', t2) == reporter.log[20]
        assert ('start', tstop) == reporter.log[21]
        assert ('up-to-date', tstop) == reporter.log[22]
        # modify t1
        assert ('start', t1) == reporter.log[23]
        assert ('execute', t1) == reporter.log[24]
        assert ('success', t1) == reporter.log[25]
        assert ('start', t2) == reporter.log[26]
        assert ('up-to-date', t2) == reporter.log[27]
        assert ('start', tstop) == reporter.log[28]
        assert ('up-to-date', tstop) == reporter.log[29]
        # modify stop
        assert ('start', t1) == reporter.log[30]
        assert ('up-to-date', t1) == reporter.log[31]
        assert ('start', t2) == reporter.log[32]
        assert ('up-to-date', t2) == reporter.log[33]
        assert ('start', tstop) == reporter.log[34]
        assert ('execute', tstop) == reporter.log[35]
        assert ('success', tstop) == reporter.log[36]
        assert 37 == len(reporter.log)
