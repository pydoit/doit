import os
import sys, StringIO

import nose.tools

from doit.core import InvalidTask, CmdTask, PythonTask
from doit.main import _create_task, _get_tasks
from doit.main import Main


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
        assert "ls.1" == tasks[1].name

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

###################

TASKS = ['string','python','dictionary','dependency','generator','func_args']
TESTDBM = "testdbm"

class TestMain(object):
    def setUp(self):
        # this test can be executed from any path
        self.fileName = os.path.abspath(__file__+"/../sample_main.py")

    # on initialization taskgen are in loaded
    def testInit(self):
        m = Main(self.fileName, TESTDBM)
        assert TASKS == m.taskgen.keys()

    def testListGenerators(self):
        m = Main(self.fileName, TESTDBM)
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        #
        m._list_generators()
        assert TASKS == sys.stdout.getvalue().split('\n')[1:-3]

        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut

    
    # test list_generators is called 
    def testProcessListGenerators(self):
        m = Main(self.fileName, TESTDBM, list=True)
        self.listed = False
        def listgen():
            self.listed = True
        m._list_generators = listgen
        m.process()
        assert self.listed

    
    def testProcessRun(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

        m = Main(self.fileName, TESTDBM)
        m.process()

        assert ["string => Cmd: ls -a",
                "python => Python: function do_nothing ",
                "dictionary => Cmd: ls -1",
                "dependency => Python: function do_nothing ",
                "generator.test_core.py => Cmd: ls -l test_core.py",
                "generator.test_util.py => Cmd: ls -l test_util.py",
                "func_args => Python: function funcX "] == \
                sys.stdout.getvalue().split("\n")[:-1]


        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut
        


    def testFilter(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

        m = Main(self.fileName, TESTDBM,filter=["dictionary","string"])
        m.process()

        assert ["dictionary => Cmd: ls -1",
                "string => Cmd: ls -a",] == \
                sys.stdout.getvalue().split("\n")[:-1]

        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut
        
