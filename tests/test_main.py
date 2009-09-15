import os
import sys, StringIO

import nose.tools

from doit.task import InvalidTask, Task
from doit.main import InvalidDodoFile, InvalidCommand
from doit.main import get_module, load_task_generators, generate_tasks
from doit.main import TaskSetup, doit_list, doit_run, doit_forget
from doit.dependency import Dependency

class TestGenerateTasks(object):

    def testDict(self):
        tasks = generate_tasks("dict",{'actions':['xpto 14']})
        assert isinstance(tasks[0],Task)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        nose.tools.assert_raises(InvalidTask, generate_tasks,"dict",
                                 {'actions':['xpto 14'],'name':'bla bla'})

    def testActionAsString(self):
        tasks = generate_tasks("dict",'xpto 14')
        assert isinstance(tasks[0],Task)


    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = generate_tasks("xpto", f_xpto())
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert "xpto:0" == tasks[1].name
        assert not tasks[0].is_subtask
        assert tasks[1].is_subtask

    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d"%i
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions' :["xpto -%d"%i]}
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())


class TestLoadTaskGenerators(object):
    def testAbsolutePath(self):
        fileName = os.path.abspath(__file__+"/../loader_sample.py")
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testRelativePath(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(__file__+"/../.."))
        fileName = "tests/loader_sample.py"
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testNameBlacklist(self):
        fileName = os.path.abspath(__file__+"/../loader_sample.py")
        dodo_module = get_module(fileName)
        nose.tools.assert_raises(InvalidDodoFile, load_task_generators,
                                 dodo_module, ['yyy2'])

    def testWrongFileName(self):
        fileName = os.path.abspath(__file__+"/../i_dont_exist.py")
        nose.tools.assert_raises(InvalidDodoFile, get_module, fileName)



class TestDodoDefaultTasks(object):
    # to avoid creating many files for testing i am modifying the module
    # dinamically. but it is tricky because python optmizes it and loads
    # it just once. so need to clean up variables that i messed up.

    def setUp(self):
        fileName = os.path.abspath(__file__+"/../loader_sample.py")
        self.dodo_module = get_module(fileName)

    def tearDown(self):
        if hasattr(self.dodo_module, 'DEFAULT_TASKS'):
            del self.dodo_module.DEFAULT_TASKS

    def testDefaultTasks_None(self):
        dodo = load_task_generators(self.dodo_module)
        assert None == dodo['default_tasks']

    def testDefaultTasks_Error(self):
        self.dodo_module.DEFAULT_TASKS = "abcd"
        nose.tools.assert_raises(InvalidDodoFile, load_task_generators,
                                 self.dodo_module)

    def testDefaultTasks_Ok(self):
        self.dodo_module.DEFAULT_TASKS = ["abcd", "add"]
        dodo = load_task_generators(self.dodo_module)
        assert ["abcd", "add"] == dodo['default_tasks']


class TestTaskSetupInit(object):

    def test_addTask(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None)
        ts = TaskSetup([t1, t2])
        assert 2 == len(ts.tasks)

    def test_targetDependency(self):
        t1 = Task("taskX", None,[],['intermediate'])
        t2 = Task("taskY", None,['intermediate'],[])
        TaskSetup([t1,t2])
        assert ['taskX'] == t2.task_dep

    # 2 tasks can not have the same name
    def test_addTaskSameName(self):
        t1 = Task("taskX", None)
        t2 = Task("taskX", None)
        nose.tools.assert_raises(InvalidDodoFile, TaskSetup, [t1, t2])

    def test_addInvalidTask(self):
        nose.tools.assert_raises(InvalidTask, TaskSetup, [666])

    def test_userErrorTaskDependency(self):
        tasks = [Task('wrong', None,[":typo"])]
        nose.tools.assert_raises(InvalidTask, TaskSetup, tasks)

    def test_sameTarget(self):
        tasks = [Task('t1',None,[],["fileX"]),
                 Task('t2',None,[],["fileX"])]
        nose.tools.assert_raises(InvalidTask, TaskSetup, tasks)



TASKS_SAMPLE = [Task("t1", [""]),
                Task("t2", [""]),
                Task("g1", None),
                Task("g1.a", [""], is_subtask=True),
                Task("g1.b", [""], is_subtask=True),
                Task("t3", [""])]
TASKS_NAME = ['t1', 't2', 'g1', 't3']
TASKS_ALL_NAME = ['t1', 't2', 'g1', 'g1.a', 'g1.b', 't3']

class TestTaskSetupFilter(object):
    def testFilter(self):
        filter_ = ['t2', 't3']
        ts = TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts._filter_tasks()

    def testFilterSubtask(self):
        filter_ = ["t1", "g1.b"]
        ts =  TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts._filter_tasks()

    def testFilterTarget(self):
        tasks = list(TASKS_SAMPLE)
        tasks.append(Task("tX", [""],[],["targetX"]))
        ts =  TaskSetup(tasks, ["targetX"])
        assert ['tX'] == ts._filter_tasks()

    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        ts =  TaskSetup(TASKS_SAMPLE, ['no'])
        nose.tools.assert_raises(InvalidCommand, ts._filter_tasks)

    def testFilterEmptyList(self):
        filter_ = []
        ts = TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts.process()


class TestOrderTasks(object):
    # same task is not added twice
    def testAddJustOnce(self):
        ts = TaskSetup([Task("taskX", None)])
        result = ts._order_tasks(["taskX"]*2)
        assert 1 == len(result)

    def testDetectCyclicReference(self):
        tasks = [Task("taskX",None,[":taskY"]),
                 Task("taskY",None,[":taskX"])]
        ts = TaskSetup(tasks)
        nose.tools.assert_raises(InvalidDodoFile, ts._order_tasks,
                                 ["taskX", "taskY"])


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
    TASKS_SAMPLE_WITH_DOC = [Task("t1", [""], doc="t1 doc string"),
                             Task("t2", [""], doc="t2 doc string"),
                             Task("g1", None, doc="g1 doc string"),
                             Task("g1.a", [""], is_subtask=True, doc="g1.a doc string"),
                             Task("g1.b", [""], is_subtask=True, doc="g1.b doc string"),
                             Task("t3", [""], doc="t3 doc string")]

    TASKS_NAME_WITH_DOC = ['%s : %s doc string' % (name, name)
                           for name in ['t1', 't2', 'g1', 't3']]

    TASKS_ALL_NAME_WITH_DOC = ['%s : %s doc string' % (name, name)
                               for name in ['t1', 't2', 'g1', 'g1.a', 'g1.b', 't3']]

    def testListTasks(self):
        doit_list(TASKS_SAMPLE, False)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert TASKS_NAME == got, sys.stdout.getvalue()

    def testListTasksWithDoc(self):
        doit_list(self.TASKS_SAMPLE_WITH_DOC, False)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert self.TASKS_NAME_WITH_DOC == got, sys.stdout.getvalue()

    def testListTasksWithDocQuiet(self):
        doit_list(self.TASKS_SAMPLE_WITH_DOC, False, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert TASKS_NAME == got, sys.stdout.getvalue()

    def testListAllTasks(self):
        doit_list(TASKS_SAMPLE, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert TASKS_ALL_NAME == got, sys.stdout.getvalue()

    def testListAllTasksWithDoc(self):
        doit_list(self.TASKS_SAMPLE_WITH_DOC, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert self.TASKS_ALL_NAME_WITH_DOC == got, sys.stdout.getvalue()

    def testListAllTasksWithDocQuiet(self):
        doit_list(self.TASKS_SAMPLE_WITH_DOC, True, True)
        got = [line for line in sys.stdout.getvalue().split('\n') if line]
        assert TASKS_ALL_NAME == got, sys.stdout.getvalue()


TESTDB = "testdb"

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
