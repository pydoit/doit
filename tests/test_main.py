import os
import sys, StringIO

import nose.tools

from doit.task import create_task
from doit.task import InvalidTask, CmdTask, PythonTask, GroupTask
from doit.main import load_task_generators
from doit.main import generate_tasks
from doit.main import InvalidCommand, InvalidDodoFile, DoitTask, Main


class TestLoadTaskGenerators(object):

    def testAbsolutePath(self):
        fileName = os.path.abspath(__file__+"/../loader_sample.py")
        expected = ["xxx1","yyy2"]
        taskgen = load_task_generators(fileName)
        assert expected == [i for i,j in taskgen]

    def testRelativePath(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(__file__+"/../.."))
        fileName = "tests/loader_sample.py"
        expected = ["xxx1","yyy2"]
        taskgen = load_task_generators(fileName)
        assert expected == [i for i,j in taskgen]


class TestGenerateTasks(object):

    def testDict(self):
        task,subtasks = generate_tasks("dict",{'action':'xpto 14'})
        assert isinstance(task,CmdTask)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        nose.tools.assert_raises(InvalidTask, generate_tasks,"dict",
                                 {'action':'xpto 14','name':'bla bla'})

    def testDictMissingFieldAction(self):
        nose.tools.assert_raises(InvalidTask, generate_tasks,
                                 "dict",{'acTion':'xpto 14'})

    def testAction(self):
        task,subtasks = generate_tasks("dict",'xpto 14')
        assert isinstance(task,CmdTask)


    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'action' :"xpto -%d"%i}
        task,subtasks = generate_tasks("xpto", f_xpto())
        assert None == task
        assert 3 == len(subtasks)
        assert "xpto:1" == subtasks[1].name

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


class TestAddToRunner(object):

    def setUp(self):
        class MockRunner:
            taskCount = 0
            def add_task(self,task):self.taskCount += 1
        self.runner = MockRunner()

    def testStatusSet(self):
        baseTask = create_task("taskX","xpto 14 7",[],[])
        doitTask = DoitTask(baseTask,[])
        assert DoitTask.UNUSED == doitTask.status
        doitTask.add_to(self.runner.add_task)
        assert DoitTask.ADDED == doitTask.status

    # same task is not added twice
    def testAddJustOnce(self):
        baseTask = create_task("taskX","xpto 14 7",[],[])
        doitTask = DoitTask(baseTask,[])
        assert 0 == self.runner.taskCount
        doitTask.add_to(self.runner.add_task)
        assert 1 == self.runner.taskCount
        doitTask.add_to(self.runner.add_task)
        assert 1 == self.runner.taskCount

    def testDetectCyclicReference(self):
        baseTask1 = create_task("taskX","xpto 14 7",[],[])
        baseTask2 = create_task("taskX","xpto 14 7",[],[])
        doitTask1 = DoitTask(baseTask1,[])
        doitTask2 = DoitTask(baseTask2,[doitTask1])
        doitTask1.dependsOn = [doitTask2]

        nose.tools.assert_raises(InvalidDodoFile,doitTask1.add_to,
                                 self.runner.add_task)


###################
# FIXME: this are more like system tests.
# i must create a dodo file to test the processing part, but i should not.

# Main class needs to be split up. the load
# expected values from sample_main.py
TASKS = ['string','python','dictionary','dependency','generator','func_args',
         'taskdependency','targetdependency','mygroup']
ALLTASKS = ['string','python','dictionary','dependency','generator',
            'generator:test_runner.py','generator:test_util.py','func_args',
            'taskdependency','targetdependency','mygroup']
TESTDBM = "testdbm"
DODO_FILE = os.path.abspath(__file__+"/../sample_main.py")
# sample dodo file with user error on task dependency name.
ETD_DODO_FILE = os.path.abspath(__file__+"/../sample_uetd.py")


class TestMain(object):
    def setUp(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)
        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut


    # on initialization taskgen are in loaded
    def testInit(self):
        m = Main(DODO_FILE, TESTDBM)
        assert TASKS == [i for i,j in m.taskgen]

    def testListTasks(self):
        m = Main(DODO_FILE, TESTDBM)
        m._list_tasks(False)
        assert TASKS == sys.stdout.getvalue().split('\n')[1:-3]

    def testListAllTasks(self):
        m = Main(DODO_FILE, TESTDBM)
        m._list_tasks(True)
        assert ALLTASKS == sys.stdout.getvalue().split('\n')[1:-3]

    # test list_tasks is called
    def testProcessListTasks(self):
        m = Main(DODO_FILE, TESTDBM, list_=1)
        self.listed = False
        def listgen(printSubtasks):
            if not printSubtasks:
                self.listed = True
        m._list_tasks = listgen
        m.process()
        assert self.listed

    def testProcessListAllTasks(self):
        m = Main(DODO_FILE, TESTDBM, list_=2)
        self.listed = False
        def listgen(printSubtasks):
            if printSubtasks:
                self.listed = True
        m._list_tasks = listgen
        m.process()
        assert self.listed


    def testProcessRun(self):
        m = Main(DODO_FILE, TESTDBM)
        m.process()
        assert [
            "string => Cmd: python sample_process.py sss",
            "python => Python: function do_nothing",
            "dictionary => Cmd: python sample_process.py ddd",
            "dependency => Python: function do_nothing",
            "generator:test_runner.py => Cmd: python sample_process.py test_runner.py",
            "generator:test_util.py => Cmd: python sample_process.py test_util.py",
            "func_args => Python: function funcX",
            "taskdependency => Python: function do_nothing",
            "targetdependency => Python: function do_nothing",
            "mygroup => Group: :dictionary, :string"] == \
            sys.stdout.getvalue().split("\n")[:-1], sys.stdout.getvalue()


    def testFilter(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["dictionary","string"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "string => Cmd: python sample_process.py sss",] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testFilterSubtask(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["generator:test_util.py"])
        m.process()
        expect = ("generator:test_util.py => " +
                  "Cmd: python sample_process.py test_util.py")
        assert [expect,] == sys.stdout.getvalue().split("\n")[:-1]

    def testFilterTarget(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["test_runner.py"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",] == \
                sys.stdout.getvalue().split("\n")[:-1]


    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["XdictooonaryX","string"])
        nose.tools.assert_raises(InvalidCommand,m.process)


    def testGroup(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["mygroup"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "string => Cmd: python sample_process.py sss",
                "mygroup => Group: :dictionary, :string"] == \
                sys.stdout.getvalue().split("\n")[:-1], sys.stdout.getvalue()


    def testTaskDependency(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["taskdependency"])
        m.process()
        assert ["generator:test_runner.py => Cmd: python sample_process.py test_runner.py",
                "generator:test_util.py => Cmd: python sample_process.py test_util.py",
                "taskdependency => Python: function do_nothing"] == \
                sys.stdout.getvalue().split("\n")[:-1]


    def testTargetDependency(self):
        m = Main(DODO_FILE, TESTDBM,filter_=["targetdependency"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "targetdependency => Python: function do_nothing"] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testUserErrorTaskDependency(self):
        m = Main(ETD_DODO_FILE, TESTDBM)
        nose.tools.assert_raises(InvalidTask,m.process)


