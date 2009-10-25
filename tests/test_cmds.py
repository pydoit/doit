import sys
import os
import StringIO

import nose

from doit.dependency import Dependency
from doit.task import Task
from doit.cmds import doit_list, doit_run, doit_clean, doit_forget
from doit.main import InvalidCommand


TESTDB = os.path.join(os.path.dirname(__file__), "testdb")

def tearDownModule(self):
    if os.path.exists(TESTDB):
        os.remove(TESTDB)


TASKS_SAMPLE = [Task("t1", [""], doc="t1 doc string"),
                Task("t2", [""], doc="t2 doc string"),
                Task("g1", None, doc="g1 doc string"),
                Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
                Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
                Task("t3", [""], doc="t3 doc string")]


class BaseTestOutput(object):
    """base class for tests that use stdout"""
    def setUp(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut


class TestCmdList(BaseTestOutput):

    def testListTasksWithDoc(self):
        doit_list(TASKS_SAMPLE, False)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        expected = []
        for t in TASKS_SAMPLE:
            if not t.is_subtask:
                expected.append("%s : %s" % (t.name, t.doc))
        assert expected == got, sys.stdout.getvalue()

    def testListTasksWithDocQuiet(self):
        doit_list(TASKS_SAMPLE, False, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE if not t.is_subtask]
        assert expected == got, sys.stdout.getvalue()

    def testListAllTasksWithDoc(self):
        doit_list(TASKS_SAMPLE, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        expected = ["%s : %s" % (t.name, t.doc) for t in TASKS_SAMPLE]
        assert expected == got, sys.stdout.getvalue()

    def testListAllTasksWithDocQuiet(self):
        doit_list(TASKS_SAMPLE, True, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        expected = [t.name for t in TASKS_SAMPLE]
        assert expected == got, sys.stdout.getvalue()



class TestCmdForget(BaseTestOutput):
    def setUp(self):
        BaseTestOutput.setUp(self)
        if os.path.exists(TESTDB):
            os.remove(TESTDB)

        self.tasks = [Task("t1", [""]),
                      Task("t2", [""]),
                      Task("g1", None, (':g1.a',':g1.b')),
                      Task("g1.a", [""]),
                      Task("g1.b", [""]),
                      Task("t3", [""], (':t1',)),
                      Task("g2", None, (':t1',':g1'))]

        dep = Dependency(TESTDB)
        for task in self.tasks:
            dep._set(task.name,"dep","1")
        dep.close()


    def testForgetAll(self):
        doit_forget(TESTDB, self.tasks, [])
        got = sys.stdout.getvalue().split("\n")[:-1]
        assert ["forgeting all tasks"] == got, repr(sys.stdout.getvalue())
        dep = Dependency(TESTDB)
        for task in self.tasks:
            assert None == dep._get(task.name, "dep")

    def testForgetOne(self):
        doit_forget(TESTDB, self.tasks, ["t2", "t1"])
        got = sys.stdout.getvalue().split("\n")[:-1]
        assert ["forgeting t2", "forgeting t1"] == got
        dep = Dependency(TESTDB)
        assert None == dep._get("t1", "dep")
        assert None == dep._get("t2", "dep")

    def testForgetGroup(self):
        doit_forget(TESTDB, self.tasks, ["g2"])
        got = sys.stdout.getvalue().split("\n")[:-1]

        dep = Dependency(TESTDB)
        assert None == dep._get("t1", "dep"), got
        assert "1" == dep._get("t2", "dep")
        assert None == dep._get("g1", "dep")
        assert None == dep._get("g1.a", "dep")
        assert None == dep._get("g1.b", "dep")
        assert None == dep._get("g2", "dep")

    # if task dependency not from a group dont forget it
    def testDontForgetTaskDependency(self):
        doit_forget(TESTDB, self.tasks, ["t3"])
        got = sys.stdout.getvalue().split("\n")[:-1]
        dep = Dependency(TESTDB)
        assert None == dep._get("t3", "dep")
        assert "1" == dep._get("t1", "dep")

    def testForgetInvalid(self):
        nose.tools.assert_raises(InvalidCommand,
                                 doit_forget, TESTDB, self.tasks, ["XXX"])


class TestCmdRun(BaseTestOutput):

    def setUp(self):
        BaseTestOutput.setUp(self)
        if os.path.exists(TESTDB):
            os.remove(TESTDB)

    def testProcessRun(self):
        doit_run(TESTDB, TASKS_SAMPLE)
        got = sys.stdout.getvalue().split("\n")[:-1]

        assert ["t1 => Cmd: ",
                "t2 => Cmd: ",
                "g1 => Group: ",
                "g1.a => Cmd: ",
                "g1.b => Cmd: ",
                "t3 => Cmd: "] == got, repr(sys.stdout.getvalue())

    def testProcessRunFilter(self):
        doit_run(TESTDB, TASKS_SAMPLE, filter_=["g1.a"])
        got = sys.stdout.getvalue().split("\n")[:-1]
        assert ["g1.a => Cmd: "] == got, repr(sys.stdout.getvalue())

    def testInvalidReporter(self):
        nose.tools.assert_raises(InvalidCommand,
               doit_run, TESTDB, TASKS_SAMPLE, reporter="i dont exist")


class TestCmdClean(BaseTestOutput):

    def setUp(self):
        BaseTestOutput.setUp(self)
        self.count = 0
        self.tasks = [Task("t1", None, clean=[(self.increment,)]),
                      Task("t2", None, clean=[(self.increment,)]),
                      ]

    def increment(self):
        self.count += 1
        return True

    def test_clean_all(self):
        doit_clean(self.tasks, [])
        assert 2 == self.count

    def test_clean_selected(self):
        doit_clean(self.tasks, ['t2'])
