import os
import StringIO
import threading
import time

import pytest

from doit.dependency import Dependency
from doit.task import Task
from doit.exceptions import InvalidCommand
from doit import cmds
from doit import reporter
from tests.test_runner import FakeReporter
from tests.conftest import remove_db


def tasks_sample():
    tasks_sample = [
        Task("t1", [""], doc="t1 doc string"),
        Task("t2", [""], doc="t2 doc string"),
        Task("g1", None, doc="g1 doc string"),
        Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
        Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
        Task("t3", [""], doc="t3 doc string")]
    tasks_sample[2].task_dep = ['g1.a', 'g1.b']
    return tasks_sample


class TestCmdList(object):

    def testDefault(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmds.doit_list(depfile.name, tasks, output, [])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in tasks if not t.is_subtask]
        assert sorted(expected) == got

    def testDoc(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmds.doit_list(depfile.name, tasks, output, [], print_doc=True)
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
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, [my_task], output, [],
                       print_dependencies=True)
        got = output.getvalue()
        assert "d2.txt" in got

    def testSubTask(self, depfile):
        output = StringIO.StringIO()
        tasks = tasks_sample()
        cmds.doit_list(depfile.name, tasks, output, [], print_subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in sorted(tasks)]
        assert expected == got

    def testFilter(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, tasks_sample(), output, ['g1', 't2'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testFilterSubtask(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, tasks_sample(), output, ['g1.a'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1.a']
        assert expected == got

    def testFilterAll(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, tasks_sample(), output, ['g1'],
                       print_subtasks=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, tasks_sample(), output, ['g1'],
                       print_status=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['R g1']
        assert expected == got

    def testNoPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, task_list, output, ['_s3'])
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = []
        assert expected == got

    def testWithPrivate(self, depfile):
        task_list = list(tasks_sample())
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmds.doit_list(depfile.name, task_list, output, ['_s3'],
                       print_private=True)
        got = [line.strip() for line in output.getvalue().split('\n') if line]
        expected = ['_s3']
        assert expected == got


class TestCmdForget(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            tasks = [Task("t1", [""]),
                     Task("t2", [""]),
                     Task("g1", None, task_dep=['g1.a','g1.b']),
                     Task("g1.a", [""]),
                     Task("g1.b", [""]),
                     Task("t3", [""], task_dep=['t1']),
                     Task("g2", None, task_dep=['t1','g1'])]
            return tasks
        return request.cached_setup(
            setup=create_tasks,
            scope="function")

    @staticmethod
    def _add_task_deps(tasks, testdb):
        """put some data on testdb"""
        dep = Dependency(testdb)
        for task in tasks:
            dep._set(task.name,"dep","1")
        dep.close()

        dep2 = Dependency(testdb)
        assert "1" == dep2._get("g1.a", "dep")
        dep2.close()


    def testForgetAll(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        cmds.doit_forget(depfile.name, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
#        assert False
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        cmds.doit_forget(depfile.name, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(depfile.name)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")
        assert "1" == dep._get("g1.a", "dep")

    def testForgetGroup(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        cmds.doit_forget(depfile.name, tasks, output, ["g2"])
        got = output.getvalue().split("\n")[:-1]
        assert "forgeting g2" == got[0]

        dep = Dependency(depfile.name)
        assert None == dep._get("t1", "dep")
        assert "1" == dep._get("t2", "dep")
        assert None == dep._get("g1", "dep")
        assert None == dep._get("g1.a", "dep")
        assert None == dep._get("g1.b", "dep")
        assert None == dep._get("g2", "dep")

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        cmds.doit_forget(depfile.name, tasks, output, ["t3"])
        dep = Dependency(depfile.name)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks, depfile):
        self._add_task_deps(tasks, depfile.name)
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, cmds.doit_forget,
                       depfile.name, tasks, output, ["XXX"])


class TestCmdRun(object):

    def testProcessRun(self, depfile):
        output = StringIO.StringIO()
        result = cmds.doit_run(depfile.name, tasks_sample(), output)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunMP(self, depfile):
        output = StringIO.StringIO()
        result = cmds.doit_run(depfile.name, tasks_sample(), output, num_process=1)
        assert 0 == result
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunFilter(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_run(depfile.name, tasks_sample(), output, ["g1.a"])
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got, repr(got)

    def testProcessRunEmptyFilter(self, depfile):
        output = StringIO.StringIO()
        cmds.doit_run(depfile.name, tasks_sample(), output, [])
        got = output.getvalue().split("\n")[:-1]
        assert [] == got

    def testInvalidReporter(self, depfile):
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, cmds.doit_run,
                depfile.name, tasks_sample(), output, reporter="i dont exist")

    def testCustomReporter(self, depfile):
        output = StringIO.StringIO()
        class MyReporter(reporter.ConsoleReporter):
            def get_status(self, task):
                self.outstream.write('MyReporter.start %s\n' % task.name)
        cmds.doit_run(depfile.name, [tasks_sample()[0]], output, reporter=MyReporter)
        got = output.getvalue().split("\n")[:-1]
        assert 'MyReporter.start t1' == got[0]

    def testSetVerbosity(self, depfile):
        output = StringIO.StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        cmds.doit_run(depfile.name, [t], output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity

    def test_outfile(self, depfile):
        cmds.doit_run(depfile.name, tasks_sample(), 'test.out', ["g1.a"])
        try:
            outfile = open('test.out', 'r')
            got = outfile.read()
            outfile.close()
            assert ".  g1.a\n" == got, repr(got)
        finally:
            if os.path.exists('test.out'):
                os.remove('test.out')


class TestCmdClean(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            self.cleaned = []
            def myclean(name):
                self.cleaned.append(name)
            self.tasks = [Task("t1", None, task_dep=['t2'],
                               clean=[(myclean,('t1',))]),
                          Task("t2", None, clean=[(myclean,('t2',))]),]
        return request.cached_setup(
            setup=create_tasks,
            scope="function")

    def test_clean_all(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_clean(self.tasks, output, False, False, [])
        assert ['t1','t2'] == self.cleaned

    def test_clean_selected(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_clean(self.tasks, output, False, False, ['t2'])
        assert ['t2'] == self.cleaned

    def test_clean_taskdep(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_clean(self.tasks, output, False, True, ['t1'])
        assert ['t2', 't1'] == self.cleaned

    def test_clean_taskdep_once(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_clean(self.tasks, output, False, True, ['t1', 't2'])
        assert ['t2', 't1'] == self.cleaned


class TestCmdIgnore(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            # FIXME DRY
            tasks = [Task("t1", [""]),
                     Task("t2", [""]),
                     Task("g1", None, task_dep=['g1.a','g1.b']),
                     Task("g1.a", [""]),
                     Task("g1.b", [""]),
                     Task("t3", [""], task_dep=['t1']),
                     Task("g2", None, task_dep=['t1','g1'])]
            return tasks
        return request.cached_setup(
            setup=create_tasks,
            scope="function")



    def testIgnoreAll(self, tasks, depfile):
        output = StringIO.StringIO()
        cmds.doit_ignore(depfile.name, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        dep = Dependency(depfile.name)
        for task in tasks:
            assert None == dep._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks, depfile):
        output = StringIO.StringIO()
        cmds.doit_ignore(depfile.name, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(depfile.name)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks, depfile):
        output = StringIO.StringIO()
        cmds.doit_ignore(depfile.name, tasks, output, ["g2"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(depfile.name)
        assert '1' == dep._get("t1", "ignore:"), got
        assert None == dep._get("t2", "ignore:")
        assert '1' == dep._get("g1", "ignore:")
        assert '1' == dep._get("g1.a", "ignore:")
        assert '1' == dep._get("g1.b", "ignore:")
        assert '1' == dep._get("g2", "ignore:")

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self, tasks, depfile):
        output = StringIO.StringIO()
        cmds.doit_ignore(depfile.name, tasks, output, ["t3"])
        dep = Dependency(depfile.name)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks, depfile):
        output = StringIO.StringIO()
        pytest.raises(InvalidCommand, cmds.doit_ignore,
                       depfile.name, tasks, output, ["XXX"])



class TestCmdAuto(object):

    def test_watch(self, cwd, depfile):
        t1 = Task("t1", None, file_dep=["f1"])
        t2 = Task("t2", None, file_dep=["f2"], calc_dep=["t1"])
        # simple task
        w1_tasks, w1_files = cmds._auto_watch([t1, t2], ["t1"])
        assert ["t1"] == w1_tasks
        assert ["f1"] == w1_files
        # with calc_dep
        w2_tasks, w2_files = cmds._auto_watch([t1, t2], ["t2"])
        assert ["t1", "t2"] == w2_tasks
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
        monkeypatch.setattr(cmds.FileModifyWatcher, "_handle", _handle)
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
        run_args = (depfile.name, task_list, ["t1", "t2", "stop"],
                    None, reporter, loop_callback)
        loop_thread = threading.Thread(target=cmds.doit_auto, args=run_args)
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

        sleep_factor = 0.1 # ensure execution is over before start a new one
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
