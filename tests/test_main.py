import os
import sys, StringIO

import nose.tools

from doit.task import InvalidTask, CmdTask, PythonTask
from doit.main import InvalidCommand, InvalidDodoFile, DoitTask, Main


def dumb(): return

class TestCreateTask(object):

    # you can pass a cmd as a sequence
    def testStringTask(self):
        task = DoitTask._create_task("taskX","ls -1 -a")
        assert isinstance(task, CmdTask)

    def testPythonTask(self):
        task = DoitTask._create_task("taskX",dumb)
        assert isinstance(task, PythonTask)

    def testInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,DoitTask._create_task,"taskX",self)
        

class TestGetTasks(object):

    def testDict(self):
        task,subtasks = DoitTask.get_tasks("dict",{'action':'ls -a'})
        assert isinstance(task,CmdTask)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,"dict",
                                 {'action':'ls -a','name':'bla bla'})

    def testDictMissingFieldAction(self):
        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,
                                 "dict",{'acTion':'ls -a'})

    def testAction(self):
        task,subtasks = DoitTask.get_tasks("dict",'ls -a')
        assert isinstance(task,CmdTask)


    def testGenerator(self):
        def ls():
            for i in range(3):
                yield {'name':str(i), 'action' :"ls -%d"%i}

        task,subtasks = DoitTask.get_tasks("ls", ls())
        assert None == task
        assert 3 == len(subtasks)
        assert "ls:1" == subtasks[1].name

    def testGeneratorDoesntReturnDict(self):
        def ls():
            for i in range(3):
                yield "ls -%d"%i

        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,"ls", ls())

    def testGeneratorDictMissingName(self):
        def ls():
            for i in range(3):
                yield {'action' :"ls -%d"%i}

        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,"ls", ls())

    def testGeneratorDictMissingAction(self):
        def ls():
            for i in range(3):
                yield {'name':str(i)}

        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,"ls", ls())


    def testDictFieldTypo(self):
        nose.tools.assert_raises(InvalidTask,DoitTask.get_tasks,
                                 "dict",{'action':'ls -a','target':['xxx']})


class TestAddToRunner(object):
    
    def setUp(self):
        class MockRunner: 
            taskCount = 0
            def add_task(self,task):self.taskCount += 1

        self.runner = MockRunner()
    
    def testStatusSet(self):
        baseTask = DoitTask._create_task("taskX","ls -1 -a")
        doitTask = DoitTask(baseTask,[])
        assert DoitTask.UNUSED == doitTask.status
        doitTask.add_to(self.runner.add_task)
        assert DoitTask.ADDED == doitTask.status

    # same task is not added twice
    def testAddJustOnce(self):
        baseTask = DoitTask._create_task("taskX","ls -1 -a")
        doitTask = DoitTask(baseTask,[])
        assert 0 == self.runner.taskCount
        doitTask.add_to(self.runner.add_task)
        assert 1 == self.runner.taskCount
        doitTask.add_to(self.runner.add_task)
        assert 1 == self.runner.taskCount

    def testDetectCyclicReference(self):
        baseTask1 = DoitTask._create_task("taskX","ls -1 -a")
        baseTask2 = DoitTask._create_task("taskX","ls -1 -a")
        doitTask1 = DoitTask(baseTask1,[])
        doitTask2 = DoitTask(baseTask2,[doitTask1])
        doitTask1.dependsOn = [doitTask2]        
        
        nose.tools.assert_raises(InvalidDodoFile,doitTask1.add_to,
                                 self.runner.add_task)

        
    
###################

TASKS = ['string','python','dictionary','dependency','generator','func_args',
         'taskdependency','targetdependency']
ALLTASKS = ['string','python','dictionary','dependency','generator',
            'generator:test_runner.py','generator:test_util.py','func_args',
            'taskdependency','targetdependency']
TESTDBM = "testdbm"

class TestMain(object):
    def setUp(self):
        # this test can be executed from any path
        self.fileName = os.path.abspath(__file__+"/../sample_main.py")
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
        m = Main(self.fileName, TESTDBM)
        assert TASKS == m.taskgen.keys()

    def testListTasks(self):
        m = Main(self.fileName, TESTDBM)
        m._list_tasks(False)
        assert TASKS == sys.stdout.getvalue().split('\n')[1:-3]

    def testListAllTasks(self):
        m = Main(self.fileName, TESTDBM)
        m._list_tasks(True)
        assert ALLTASKS == sys.stdout.getvalue().split('\n')[1:-3]
    
    # test list_tasks is called 
    def testProcessListTasks(self):
        m = Main(self.fileName, TESTDBM, list_=1)
        self.listed = False
        def listgen(printSubtasks):
            if not printSubtasks:
                self.listed = True
        m._list_tasks = listgen
        m.process()
        assert self.listed

    def testProcessListAllTasks(self):
        m = Main(self.fileName, TESTDBM, list_=2)
        self.listed = False
        def listgen(printSubtasks):
            if printSubtasks:
                self.listed = True
        m._list_tasks = listgen
        m.process()
        assert self.listed

    
    def testProcessRun(self):
        m = Main(self.fileName, TESTDBM)
        m.process()
        assert ["string => Cmd: ls -a",
                "python => Python: function do_nothing",
                "dictionary => Cmd: ls -1",
                "dependency => Python: function do_nothing",
                "generator:test_runner.py => Cmd: ls -l test_runner.py",
                "generator:test_util.py => Cmd: ls -l test_util.py",
                "func_args => Python: function funcX",
                "taskdependency => Cmd: ls",
                "targetdependency => Cmd: ls"] == \
                sys.stdout.getvalue().split("\n")[:-1]



    def testFilter(self):
        m = Main(self.fileName, TESTDBM,filter_=["dictionary","string"])
        m.process()
        assert ["dictionary => Cmd: ls -1",
                "string => Cmd: ls -a",] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testFilterSubtask(self):
        m = Main(self.fileName, TESTDBM,filter_=["generator:test_util.py"])
        m.process()
        assert ["generator:test_util.py => Cmd: ls -l test_util.py",] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testFilterTarget(self):
        m = Main(self.fileName, TESTDBM,filter_=["test_runner.py"])
        m.process()
        assert ["dictionary => Cmd: ls -1",] == \
                sys.stdout.getvalue().split("\n")[:-1]        
        
    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        m = Main(self.fileName, TESTDBM,filter_=["XdictooonaryX","string"])
        nose.tools.assert_raises(InvalidCommand,m.process)

    def testTaskDependency(self):
        m = Main(self.fileName, TESTDBM,filter_=["taskdependency"])
        m.process()
        assert ["generator:test_runner.py => Cmd: ls -l test_runner.py",
                "generator:test_util.py => Cmd: ls -l test_util.py",
                "taskdependency => Cmd: ls"] == \
                sys.stdout.getvalue().split("\n")[:-1]
        
        
    def testTargetDependency(self):
        m = Main(self.fileName, TESTDBM,filter_=["targetdependency"])
        m.process()
        assert ["dictionary => Cmd: ls -1",
                "targetdependency => Cmd: ls"] == \
                sys.stdout.getvalue().split("\n")[:-1]
        

        
