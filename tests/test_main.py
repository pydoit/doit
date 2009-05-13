import os
import sys, StringIO

import nose.tools

from doit.task import create_task
from doit.task import InvalidTask, CmdTask, GroupTask
from doit.main import load_task_generators
from doit.main import generate_tasks, get_tasks
from doit.main import InvalidCommand, Main, CmdList
from doit.main import InvalidDodoFile

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
        assert isinstance(tasks[-1], GroupTask)
        assert 4 == len(tasks)
        assert "xpto:1" == tasks[1].name

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



###################

class TestOrderTasks(object):
    # same task is not added twice
    def testAddJustOnce(self):
        baseTask = create_task("taskX","xpto 14 7",[],[])
        m = Main(None, {"taskX": baseTask})
        result = m._order_tasks(["taskX"]*2)
        assert 1 == len(result)

    def testDetectCyclicReference(self):
        baseTask1 = create_task("taskX",None,[":taskY"],[])
        baseTask2 = create_task("taskY",None,[":taskX"],[])
        tasks = {"taskX": baseTask1, "taskY": baseTask2}
        m = Main(None, tasks)
        nose.tools.assert_raises(InvalidDodoFile, m._order_tasks,
                                 ["taskX", "taskY"])



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


class TestListCmd(object):
    def setUp(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.taskgen = load_task_generators(DODO_FILE)
        self.tasks = get_tasks(self.taskgen)

    def tearDown(self):
        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut


    def testListTasks(self):
        m = CmdList(self.taskgen, self.tasks)
        m.process(False)
        assert TASKS == sys.stdout.getvalue().split('\n')[1:-3]

    def testListAllTasks(self):
        m = CmdList(self.taskgen, self.tasks)
        m.process(True)
        assert ALLTASKS == sys.stdout.getvalue().split('\n')[1:-3], sys.stdout.getvalue()




class TestMain(object):
    def setUp(self):
        #setup stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        taskgen = load_task_generators(DODO_FILE)
        self.tasks = get_tasks(taskgen)

    def tearDown(self):
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)
        #teardown stdout
        sys.stdout.close()
        sys.stdout = self.oldOut


    def testProcessRun(self):
        m = Main(TESTDBM, self.tasks)
        m.process()
        assert [
            "string => Cmd: python sample_process.py sss",
            "python => Python: function do_nothing",
            "dictionary => Cmd: python sample_process.py ddd",
            "dependency => Python: function do_nothing",
            "generator:test_runner.py => Cmd: python sample_process.py test_runner.py",
            "generator:test_util.py => Cmd: python sample_process.py test_util.py",
            "generator => Group: ",
            "func_args => Python: function funcX",
            "taskdependency => Python: function do_nothing",
            "targetdependency => Python: function do_nothing",
            "mygroup => Group: :dictionary, :string"] == \
            sys.stdout.getvalue().split("\n")[:-1], repr(sys.stdout.getvalue())


    def testFilter(self):
        m = Main(TESTDBM, self.tasks, filter_=["dictionary","string"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "string => Cmd: python sample_process.py sss",] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testFilterSubtask(self):
        m = Main(TESTDBM, self.tasks, filter_=["generator:test_util.py"])
        m.process()
        expect = ("generator:test_util.py => " +
                  "Cmd: python sample_process.py test_util.py")
        assert [expect,] == sys.stdout.getvalue().split("\n")[:-1]

    def testFilterTarget(self):
        m = Main(TESTDBM, self.tasks, filter_=["test_runner.py"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",] == \
                sys.stdout.getvalue().split("\n")[:-1]


    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        m = Main(TESTDBM, self.tasks, filter_=["XdictooonaryX","string"])
        nose.tools.assert_raises(InvalidCommand,m.process)


    def testGroup(self):
        m = Main(TESTDBM, self.tasks, filter_=["mygroup"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "string => Cmd: python sample_process.py sss",
                "mygroup => Group: :dictionary, :string"] == \
                sys.stdout.getvalue().split("\n")[:-1], sys.stdout.getvalue()


    def testTaskDependency(self):
        m = Main(TESTDBM, self.tasks, filter_=["taskdependency"])
        m.process()
        assert ["generator:test_runner.py => Cmd: python sample_process.py test_runner.py",
                "generator:test_util.py => Cmd: python sample_process.py test_util.py",
                "generator => Group: ",
                "taskdependency => Python: function do_nothing"] == \
                sys.stdout.getvalue().split("\n")[:-1], sys.stdout.getvalue()


    def testTargetDependency(self):
        m = Main(TESTDBM, self.tasks, filter_=["targetdependency"])
        m.process()
        assert ["dictionary => Cmd: python sample_process.py ddd",
                "targetdependency => Python: function do_nothing"] == \
                sys.stdout.getvalue().split("\n")[:-1]

    def testUserErrorTaskDependency(self):
        tt = GroupTask('wrong', None,[":typo"])
        tasks = {'wrong': tt}
        m = Main(TESTDBM, tasks)
        nose.tools.assert_raises(InvalidTask, m.process)
