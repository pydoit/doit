import os
import sys, StringIO

import nose.tools

from doit.task import create_task
from doit.task import InvalidTask, CmdTask, GroupTask
from doit.main import load_task_generators
from doit.main import generate_tasks
from doit.main import InvalidCommand, cmd_list, cmd_run
from doit.main import InvalidDodoFile, TaskSetup

class TestGenerateTasks(object):

    def testDict(self):
        tasks = generate_tasks("dict",{'action':'xpto 14'})
        assert isinstance(tasks[0],CmdTask)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        nose.tools.assert_raises(InvalidTask, generate_tasks,"dict",
                                 {'action':'xpto 14','name':'bla bla'})

    def testDictMissingFieldAction(self):
        nose.tools.assert_raises(InvalidTask, generate_tasks,
                                 "dict",{'acTion':'xpto 14'})

    def testAction(self):
        tasks = generate_tasks("dict",'xpto 14')
        assert isinstance(tasks[0],CmdTask)


    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'action' :"xpto -%d"%i}
        tasks = generate_tasks("xpto", f_xpto())
        assert isinstance(tasks[0], GroupTask)
        assert 4 == len(tasks)
        assert "xpto:0" == tasks[1].name
        assert not tasks[0].isSubtask
        assert tasks[1].isSubtask

    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d"%i
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'action' :"xpto -%d"%i}
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        nose.tools.assert_raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testDictFieldTypo(self):
        dict_ = {'action':'xpto 14','typo_here':['xxx']}
        nose.tools.assert_raises(InvalidTask, generate_tasks, "dict", dict_)


class TestLoadTaskGenerators(object):
    def testAbsolutePath(self):
        fileName = os.path.abspath(__file__+"/../loader_sample.py")
        expected = ["xxx1","yyy2"]
        task_list = load_task_generators(fileName)
        assert expected == [t.name for t in task_list]

    def testRelativePath(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(__file__+"/../.."))
        fileName = "tests/loader_sample.py"
        expected = ["xxx1","yyy2"]
        task_list = load_task_generators(fileName)
        assert expected == [t.name for t in task_list]


class TestTaskSetupInit(object):

    def test_addTask(self):
        t1 = GroupTask("taskX", None)
        t2 = GroupTask("taskY", None)
        ts = TaskSetup([t1, t2])
        assert 2 == len(ts.tasks)

    def test_targetDependency(self):
        t1 = GroupTask("taskX", None,[],['intermediate'])
        t2 = GroupTask("taskY", None,['intermediate'],[])
        TaskSetup([t1,t2])
        assert ['taskX'] == t2.task_dep

    # 2 tasks can not have the same name
    def test_addTaskSameName(self):
        t1 = GroupTask("taskX", None)
        t2 = GroupTask("taskX", None)
        nose.tools.assert_raises(InvalidDodoFile, TaskSetup, [t1, t2])

    def test_addInvalidTask(self):
        nose.tools.assert_raises(InvalidTask, TaskSetup, [666])

    def testUserErrorTaskDependency(self):
        tasks = [GroupTask('wrong', None,[":typo"])]
        nose.tools.assert_raises(InvalidTask, TaskSetup, tasks)

sub1 = CmdTask("g1.a", "")
sub2 = CmdTask("g1.b", "")
sub1.isSubtask = True
sub2.isSubtask = True
TASKS_SAMPLE = [CmdTask("t1", ""),
                CmdTask("t2", ""),
                GroupTask("g1", None),
                sub1,
                sub2,
                CmdTask("t3", "")]
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
        tasks.append(CmdTask("tX", "",[],["targetX"]))
        ts =  TaskSetup(tasks, ["targetX"])
        assert ['tX'] == ts._filter_tasks()

    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        ts =  TaskSetup(TASKS_SAMPLE, ['no'])
        nose.tools.assert_raises(InvalidCommand, ts._filter_tasks)


class TestOrderTasks(object):
    # same task is not added twice
    def testAddJustOnce(self):
        ts = TaskSetup([GroupTask("taskX", None)])
        result = ts._order_tasks(["taskX"]*2)
        assert 1 == len(result)

    def testDetectCyclicReference(self):
        tasks = [GroupTask("taskX",None,[":taskY"]),
                 GroupTask("taskY",None,[":taskX"])]
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
    def testListTasks(self):
        cmd_list(TASKS_SAMPLE, False)
        assert TASKS_NAME == sys.stdout.getvalue().split('\n')[1:-3], sys.stdout.getvalue()

    def testListAllTasks(self):
        cmd_list(TASKS_SAMPLE, True)
        assert TASKS_ALL_NAME == sys.stdout.getvalue().split('\n')[1:-3], sys.stdout.getvalue()


TESTDBM = "testdbm"
class TestCmdRun(BaseTestOutput):

    def tearDown(self):
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)
        BaseTestOutput.tearDown(self)

    def testProcessRun(self):
        cmd_run(TESTDBM, TASKS_SAMPLE)
        assert ["t1 => Cmd: ",
                "t2 => Cmd: ",
                "g1 => Group: ",
                "g1.a => Cmd: ",
                "g1.b => Cmd: ",
                "t3 => Cmd: "] == sys.stdout.getvalue().split("\n")[:-1], repr(sys.stdout.getvalue())

    def testProcessRunFilter(self):
        cmd_run(TESTDBM, TASKS_SAMPLE, filter_=["g1.a"])
        assert ["g1.a => Cmd: "] == sys.stdout.getvalue().split("\n")[:-1], repr(sys.stdout.getvalue())
