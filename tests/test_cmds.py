import os
import StringIO
import threading

import py.test

from doit.dependency import Dependency
from doit.task import Task
from doit.main import InvalidCommand
from doit import cmds



TESTDB = os.path.join(os.path.dirname(__file__), "testdb")

def remove_testdb():
    if os.path.exists(TESTDB):
        os.remove(TESTDB)


TASKS_SAMPLE = [Task("t1", [""], doc="t1 doc string"),
                Task("t2", [""], doc="t2 doc string"),
                Task("g1", None, doc="g1 doc string"),
                Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
                Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
                Task("t3", [""], doc="t3 doc string")]
TASKS_SAMPLE[2].task_dep = ['g1.a', 'g1.b']


class TestCmdList(object):

    def testDefault(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, [])
        got = [line for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE if not t.is_subtask]
        assert expected == got

    def testDoc(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, [], print_doc=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        for t in TASKS_SAMPLE:
            if not t.is_subtask:
                expected.append("%s\t* %s" % (t.name, t.doc))
        assert expected == got

    def testDependencies(self):
        my_task = Task("t2", [""], dependencies=['d2.txt'])
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, [my_task], output, [], print_dependencies=True)
        got = output.getvalue()
        assert "d2.txt" in got

    def testSubTask(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, [], print_subtasks=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE]
        assert expected == got

    def testFilter(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, ['g1', 't2'])
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testFilterSubtask(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, ['g1.a'])
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['g1.a']
        assert expected == got

    def testFilterAll(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, ['g1'], print_subtasks=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self):
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, TASKS_SAMPLE, output, ['g1'], print_status=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['R g1']
        assert expected == got

    def testNoPrivate(self):
        task_list = list(TASKS_SAMPLE)
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, task_list, output, ['_s3'])
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        assert expected == got

    def testWithPrivate(self):
        task_list = list(TASKS_SAMPLE)
        task_list.append(Task("_s3", [""]))
        output = StringIO.StringIO()
        cmds.doit_list(TESTDB, task_list, output, ['_s3'], print_private=True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['_s3']
        assert expected == got


class TestCmdForget(object):

    def pytest_funcarg__tasks(self, request):
        def create_tasks():
            remove_testdb()
            tasks = [Task("t1", [""]),
                     Task("t2", [""]),
                     Task("g1", None, (':g1.a',':g1.b')),
                     Task("g1.a", [""]),
                     Task("g1.b", [""]),
                     Task("t3", [""], (':t1',)),
                     Task("g2", None, (':t1',':g1'))]
            dep = Dependency(TESTDB)
            for task in tasks:
                dep._set(task.name,"dep","1")
            dep.close()
            return tasks
        return request.cached_setup(
            setup=create_tasks,
            scope="function")


    def testForgetAll(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_forget(TESTDB, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
        dep = Dependency(TESTDB)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_forget(TESTDB, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(TESTDB)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")

    def testForgetGroup(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_forget(TESTDB, tasks, output, ["g2"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(TESTDB)
        assert None == dep._get("t1", "dep"), got
        assert "1" == dep._get("t2", "dep")
        assert None == dep._get("g1", "dep")
        assert None == dep._get("g1.a", "dep")
        assert None == dep._get("g1.b", "dep")
        assert None == dep._get("g2", "dep")

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_forget(TESTDB, tasks, output, ["t3"])
        dep = Dependency(TESTDB)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks):
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, cmds.doit_forget,
                       TESTDB, tasks, output, ["XXX"])


class TestCmdRun(object):

    def testProcessRun(self):
        remove_testdb()
        output = StringIO.StringIO()
        cmds.doit_run(TESTDB, TASKS_SAMPLE, output)
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunFilter(self):
        remove_testdb()
        output = StringIO.StringIO()
        cmds.doit_run(TESTDB, TASKS_SAMPLE, output, ["g1.a"])
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got, repr(got)

    def testInvalidReporter(self):
        remove_testdb()
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, cmds.doit_run,
                TESTDB, TASKS_SAMPLE, output, reporter="i dont exist")

    def testSetVerbosity(self):
        remove_testdb()
        output = StringIO.StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        cmds.doit_run(TESTDB, [t], output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity


    def test_outfile(self):
        remove_testdb()
        cmds.doit_run(TESTDB, TASKS_SAMPLE, 'test.out', ["g1.a"])
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
            self.tasks = [Task("t1", None, dependencies=[':t2'],
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
            remove_testdb()
            tasks = [Task("t1", [""]),
                     Task("t2", [""]),
                     Task("g1", None, (':g1.a',':g1.b')),
                     Task("g1.a", [""]),
                     Task("g1.b", [""]),
                     Task("t3", [""], (':t1',)),
                     Task("g2", None, (':t1',':g1'))]
            return tasks
        return request.cached_setup(
            setup=create_tasks,
            scope="function")



    def testIgnoreAll(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_ignore(TESTDB, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        dep = Dependency(TESTDB)
        for task in tasks:
            assert None == dep._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_ignore(TESTDB, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(TESTDB)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_ignore(TESTDB, tasks, output, ["g2"])
        got = output.getvalue().split("\n")[:-1]

        dep = Dependency(TESTDB)
        assert '1' == dep._get("t1", "ignore:"), got
        assert None == dep._get("t2", "ignore:")
        assert '1' == dep._get("g1", "ignore:")
        assert '1' == dep._get("g1.a", "ignore:")
        assert '1' == dep._get("g1.b", "ignore:")
        assert '1' == dep._get("g2", "ignore:")

    # if task dependency not from a group dont ignore it
    def testDontIgnoreTaskDependency(self, tasks):
        output = StringIO.StringIO()
        cmds.doit_ignore(TESTDB, tasks, output, ["t3"])
        dep = Dependency(TESTDB)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks):
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, cmds.doit_ignore,
                       TESTDB, tasks, output, ["XXX"])



def pytest_funcarg__cwd(request):
    """set cwd to parent folder of this file."""
    def set_cwd():
        cwd = {}
        cwd['preivous'] = os.getcwd()
        cwd['current'] = os.path.abspath(os.path.dirname(__file__))
        os.chdir(cwd['current'])
        return cwd
    def restore_cwd(cwd):
        os.chdir(cwd['preivous'])
    return request.cached_setup(
        setup=set_cwd,
        teardown=restore_cwd,
        scope="function")


class TestFileWatcher(object):
    def testInit(self, cwd):
        file1, file2 = 'data/w1.txt', 'data/w2.txt'
        fw = cmds.FileModifyWatcher((file1, file2))
        # file_list contains absolute paths
        assert os.path.abspath(file1) in fw.file_list
        assert os.path.abspath(file2) in fw.file_list
        # watch_dirs
        assert os.path.join(cwd['current'], 'data') in fw.watch_dirs

    def testHandleEventNotSubclassed(self):
        fw = cmds.FileModifyWatcher([])
        py.test.raises(NotImplementedError, fw.handle_event, None)

    def testLoop(self, cwd):
        file1, file2, file3 = 'data/w1.txt', 'data/w2.txt', 'data/w3.txt'
        stop_file = 'data/stop'
        fw = cmds.FileModifyWatcher((file1, file2, stop_file))
        events = []
        should_stop = []
        started = []
        def handle_event(event):
            events.append(event.pathname)
            if event.pathname.endswith("stop"):
                should_stop.append(True)
        fw.handle_event = handle_event

        def loop_callback(notifier):
            started.append(True)
            # force loop to stop
            if should_stop:
                raise KeyboardInterrupt
        loop_thread = threading.Thread(target=fw.loop, args=(loop_callback,))
        loop_thread.daemon = True
        loop_thread.start()

        # wait watcher to be ready
        while not started:
            assert loop_thread.isAlive()

        # write in watched file
        fd = open(file1, 'w')
        fd.write("hi")
        fd.close()
        # write in non-watched file
        fd = open(file3, 'w')
        fd.write("hi")
        fd.close()
        # write in another watched file
        fd = open(file2, 'w')
        fd.write("hi")
        fd.close()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        loop_thread.join(1)
        assert not loop_thread.isAlive()

        assert os.path.abspath(file1) == events[0]
        assert os.path.abspath(file2) == events[1]


class TestCmdAuto(object):
    def test(self, cwd, capsys):
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
        cmds.FileModifyWatcher._handle = _handle
        # stop file watcher
        def loop_callback(notifier):
            started.append(True)
            if should_stop:
                raise KeyboardInterrupt

        remove_testdb()
        # create files
        for fx in (file1, file2, file2, stop_file):
            fd = open(fx, 'w')
            fd.write("hi")
            fd.close()
        #
        task_list = [Task("t1", [""], [file1]),
                     Task("t2", [""], [file2]),
                     Task("stop", [""],  [stop_file]),]
        run_args = (TESTDB, task_list, ["t1", "t2", "stop"], loop_callback)
        loop_thread = threading.Thread(target=cmds.doit_auto, args=run_args)
        loop_thread.daemon = True
        loop_thread.start()

        # wait watcher to be ready
        while not started: assert loop_thread.isAlive()

        # write in watched file ====expected=====> .  t1
        fd = open(file1, 'w')
        fd.write("hi")
        fd.close()
        # write in non-watched file ============> None
        fd = open(file3, 'w')
        fd.write("hi")
        fd.close()
        # write in another watched file ========> .  t2
        fd = open(file2, 'w')
        fd.write("hi")
        fd.close()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        loop_thread.join(1)
        assert not loop_thread.isAlive()

        out, err = capsys.readouterr()
        out_lines = out.splitlines()
        assert '.  t1' == out_lines[0]
        assert '.  t2' == out_lines[1]

