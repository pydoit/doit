import os
import sys, StringIO

import nose.tools

from doit.core import Runner
from doit.task import InvalidTask, CmdTask

# dependencies file
TESTDBM = "testdbm"

##############
class ExecuteRunner(object):
    def setUp(self):
        self.runner = Runner(TESTDBM,0)

    def tearDown(self):
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

class TestExecuteTask(ExecuteRunner):
    
    def testAddTask(self):
        self.runner._addTask(CmdTask("taskX",["ls","bla bla"]))
        self.runner._addTask(CmdTask("taskY",["ls","-1"]))
        assert 2 == len(self.runner._tasks)

    # 2 tasks can not have the same name
    def testAddTaskSameName(self):
        self.runner._addTask(CmdTask("taskX",["ls","bla bla"]))
        t = CmdTask("taskX",["ls","-1"])
        nose.tools.assert_raises(InvalidTask,self.runner._addTask,t)

    def testInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,self.runner._addTask,666)

    def testAnyFailure(self):
        #ok
        self.runner._addTask(CmdTask("taskX",["ls"]))
        #fail
        self.runner._addTask(CmdTask("taskY",["ls","I dont exist"]))
        assert self.runner.FAILURE == self.runner.run()

    def testTuple(self):
        self.runner._addTask(CmdTask("taskX",("ls","-1")))
        self.runner._addTask(CmdTask("taskY",("ls","-1","-a")))
        assert self.runner.SUCCESS == self.runner.run()

#####################################
#     # captured streams should be show only for the tasks that failed
#     def testVerboseOnlyErrorTask(self):
#         runner = Runner(TESTDBM,0)
#         runner._addTask(PythonTask("taskX",self.write_on_stderr_success))
#         runner._addTask(PythonTask("taskY",self.raise_something))
#         assert runner.ERROR == runner.run()
#         # stderr by line
#         err = sys.stderr.getvalue().split('\n')
#         assert "this is stderr E" == err[0], err
#         # ignore traceback, compare just exception message
#         assert "TaskError: Hi i am an exception" == err[-2], err


#     # captured streams should be show only for the tasks that failed
#     def testVerboseOnlyErrorTask(self):
#         runner = Runner(TESTDBM,0)
#         runner._addTask(PythonTask("taskX",self.write_on_stdout_success))
#         runner._addTask(PythonTask("taskY",self.raise_something))
#         assert runner.ERROR == runner.run(False)
#         sys.__stderr__.write(sys.stdout.getvalue())
#         assert "this is stdout E\n" == sys.stdout.getvalue()

#########################


class TestDisplayRunningStatus(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)


    def testDisplay(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(CmdTask("taskX",["ls", "-1"]))
        runner._addTask(CmdTask("taskY",["ls","-a"]))
        assert runner.SUCCESS == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        assert runner._tasks['taskY'].title() == taskTitles[1], taskTitles

    # if task is up to date, it is displayed in a different way.
    def testDisplayUpToDate(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(CmdTask("taskX",["ls", "-1"],dependencies=[__file__]))
        assert runner.SUCCESS == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        # again
        sys.stdout = StringIO.StringIO()
        runner2 = Runner(TESTDBM,1)
        runner2._addTask(CmdTask("taskX",["ls", "-1"],dependencies=[__file__]))

        assert runner2.SUCCESS == runner2.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert "--- " +runner2._tasks['taskX'].title() == taskTitles[0]


class TestRunningTask(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

    # whenever a task fails remaining task are not executed
    def testFailureStops(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(CmdTask("taskX",["ls", "-2"]))
        runner._addTask(CmdTask("taskY",["ls","-a"]))
        assert runner.FAILURE == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0], taskTitles
        assert "Task failed" == taskTitles[1]

    # whenever there is an error executing a task,
    # remaining task are not executed
    def testErrorStops(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(CmdTask("taskX",["lsadsaf", "-2"]))
        runner._addTask(CmdTask("taskY",["ls","-a"]))
        assert runner.ERROR == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0], taskTitles
        assert "" == taskTitles[1], taskTitles
