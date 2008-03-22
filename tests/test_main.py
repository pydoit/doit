import os
import sys, StringIO

import nose.tools

from doit.task import InvalidTask, CmdTask, PythonTask
from doit.main import _create_task, _get_tasks
from doit.main import Main, InvalidCommand


def dumb(): return

class TestCreateTask(object):

    # you can pass a cmd as a sequence
    def testStringTask(self):
        task = _create_task("taskX","ls -1 -a")
        assert isinstance(task, CmdTask)

    # you can pass a cmd as a string
    def testSequenceTask(self):
        task = _create_task("taskX",('ls','-1', '-a'))
        assert isinstance(task, CmdTask)

    def testPythonTask(self):
        task = _create_task("taskX",dumb)
        assert isinstance(task, PythonTask)

    def testInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,_create_task,"taskX",self)
        

class TestGetTasks(object):

    def testDict(self):
        tasks = _get_tasks("dict",{'action':'ls -a'})
        assert 1 == len(tasks)
        assert isinstance(tasks[0],CmdTask)

    def testDictMissingFieldAction(self):
        nose.tools.assert_raises(InvalidTask,_get_tasks,
                                 "dict",{'acTion':'ls -a'})

    def testAction(self):
        tasks = _get_tasks("dict",'ls -a')
        assert 1 == len(tasks)
        assert isinstance(tasks[0],CmdTask)


    def testGenerator(self):
        def ls():
            for i in range(3):
                yield {'name':str(i), 'action' :"ls -%d"%i}

        tasks = _get_tasks("ls", ls())
        assert 3 == len(tasks)
        assert "ls:1" == tasks[1].name

    def testGeneratorDoesntReturnDict(self):
        def ls():
            for i in range(3):
                yield "ls -%d"%i

        nose.tools.assert_raises(InvalidTask,_get_tasks,"ls", ls())

    def testGeneratorDictMissingName(self):
        def ls():
            for i in range(3):
                yield {'action' :"ls -%d"%i}

        nose.tools.assert_raises(InvalidTask,_get_tasks,"ls", ls())

    def testGeneratorDictMissingAction(self):
        def ls():
            for i in range(3):
                yield {'name':str(i)}

        nose.tools.assert_raises(InvalidTask,_get_tasks,"ls", ls())


    def testDictFieldTypo(self):
        nose.tools.assert_raises(InvalidTask,_get_tasks,
                                 "dict",{'action':'ls -a','target':['xxx']})

###################

TASKS = ['string','python','dictionary','dependency','generator','func_args']
ALLTASKS = ['string','python','dictionary','dependency','generator',
            'generator:test_runner.py','generator:test_util.py','func_args']
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
        m = Main(self.fileName, TESTDBM, list=1)
        self.listed = False
        def listgen(printSubtasks):
            if not printSubtasks:
                self.listed = True
        m._list_tasks = listgen
        m.process()
        assert self.listed

    def testProcessListAllTasks(self):
        m = Main(self.fileName, TESTDBM, list=2)
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
                "func_args => Python: function funcX"] == \
                sys.stdout.getvalue().split("\n")[:-1]



    def testFilter(self):
        m = Main(self.fileName, TESTDBM,filter=["dictionary","string"])
        m.process()
        assert ["dictionary => Cmd: ls -1",
                "string => Cmd: ls -a",] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testFilterSubtask(self):
        m = Main(self.fileName, TESTDBM,filter=["generator:test_util.py"])
        m.process()
        assert ["generator:test_util.py => Cmd: ls -l test_util.py",] == \
                sys.stdout.getvalue().split("\n")[:-1]
        
    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        m = Main(self.fileName, TESTDBM,filter=["XdictooonaryX","string"])
        nose.tools.assert_raises(InvalidCommand,m.process)

        
