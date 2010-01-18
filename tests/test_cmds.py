import os
import StringIO

import py.test

from doit.dependency import Dependency
from doit.task import Task
from doit.cmds import doit_list, doit_run, doit_clean, doit_forget, doit_ignore
from doit.main import InvalidCommand


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

    def testListTasksWithDoc(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, [], False, False, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = []
        for t in TASKS_SAMPLE:
            if not t.is_subtask:
                expected.append("%s : %s" % (t.name, t.doc))
        assert expected == got, output.getvalue()

    def testListTasksWithDocQuiet(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, [], False, True, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE if not t.is_subtask]
        assert expected == got, output.getvalue()

    def testListAllTasksWithDoc(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, [], True, False, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ["%s : %s" % (t.name, t.doc) for t in TASKS_SAMPLE]
        assert expected == got

    def testListAllTasksWithDocQuiet(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, [], True, True, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE]
        assert expected == got

    def testListFilter(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, ['g1', 't2'],
                  False, True, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['g1', 't2']
        assert expected == got

    def testListFilterAll(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, ['g1'], True, True, False)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['g1', 'g1.a', 'g1.b']
        assert expected == got

    def testStatus(self):
        output = StringIO.StringIO()
        doit_list(TESTDB, TASKS_SAMPLE, output, ['g1'],
                  False, True, True)
        got = [line for line in output.getvalue().split('\n') if line]
        expected = ['R g1']
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
        doit_forget(TESTDB, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(output.getvalue())
        dep = Dependency(TESTDB)
        for task in tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self, tasks):
        output = StringIO.StringIO()
        doit_forget(TESTDB, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(TESTDB)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")

    def testForgetGroup(self, tasks):
        output = StringIO.StringIO()
        doit_forget(TESTDB, tasks, output, ["g2"])
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
        doit_forget(TESTDB, tasks, output, ["t3"])
        dep = Dependency(TESTDB)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self, tasks):
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, doit_forget,
                       TESTDB, tasks, output, ["XXX"])


class TestCmdRun(object):

    def testProcessRun(self):
        remove_testdb()
        output = StringIO.StringIO()
        doit_run(TESTDB, TASKS_SAMPLE, output)
        got = output.getvalue().split("\n")[:-1]
        assert [".  t1", ".  t2", ".  g1.a", ".  g1.b", ".  t3"] == got

    def testProcessRunFilter(self):
        remove_testdb()
        output = StringIO.StringIO()
        doit_run(TESTDB, TASKS_SAMPLE, output, ["g1.a"])
        got = output.getvalue().split("\n")[:-1]
        assert [".  g1.a"] == got, repr(got)

    def testInvalidReporter(self):
        remove_testdb()
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, doit_run,
                TESTDB, TASKS_SAMPLE, output, reporter="i dont exist")

    def testSetVerbosity(self):
        remove_testdb()
        output = StringIO.StringIO()
        t = Task('x', None)
        used_verbosity = []
        def my_execute(out, err, verbosity):
            used_verbosity.append(verbosity)
        t.execute = my_execute
        doit_run(TESTDB, [t], output, verbosity=2)
        assert 2 == used_verbosity[0], used_verbosity


    def test_outfile(self):
        remove_testdb()
        doit_run(TESTDB, TASKS_SAMPLE, 'test.out', ["g1.a"])
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
            self.count = 0
            self.tasks = [Task("t1", None, clean=[(self.increment,)]),
                          Task("t2", None, clean=[(self.increment,)]),]
        return request.cached_setup(
            setup=create_tasks,
            scope="function")

    def increment(self):
        self.count += 1
        return True

    def test_clean_all(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, [])
        assert 2 == self.count

    def test_clean_selected(self, tasks):
        output = StringIO.StringIO()
        doit_clean(self.tasks, output, ['t2'])


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
        doit_ignore(TESTDB, tasks, output, [])
        got = output.getvalue().split("\n")[:-1]
        assert ["You cant ignore all tasks! Please select a task."] == got, got
        dep = Dependency(TESTDB)
        for task in tasks:
            assert None == dep._get(task.name, "ignore:")

    def testIgnoreOne(self, tasks):
        output = StringIO.StringIO()
        doit_ignore(TESTDB, tasks, output, ["t2", "t1"])
        got = output.getvalue().split("\n")[:-1]
        assert ["ignoring t2", "ignoring t1"] == got
        dep = Dependency(TESTDB)
        assert '1' == dep._get("t1", "ignore:")
        assert '1' == dep._get("t2", "ignore:")
        assert None == dep._get("t3", "ignore:")

    def testIgnoreGroup(self, tasks):
        output = StringIO.StringIO()
        doit_ignore(TESTDB, tasks, output, ["g2"])
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
        doit_ignore(TESTDB, tasks, output, ["t3"])
        dep = Dependency(TESTDB)
        assert '1' == dep._get("t3", "ignore:")
        assert None == dep._get("t1", "ignore:")

    def testIgnoreInvalid(self, tasks):
        output = StringIO.StringIO()
        py.test.raises(InvalidCommand, doit_ignore,
                       TESTDB, tasks, output, ["XXX"])

