import os
import nose.tools

from doit.core import Runner
from doit.core import InvalidTask, BaseTask, CmdTask, PythonTask

# dependencies file
TESTDBM = "testdbm"

#############
class TestDependencyErrorMessages():

    # dependevy must be a sequence. give proper error message when anything 
    # else is used.
    def test_dependency_not_sequence(self):
        filePath = os.path.abspath(__file__+"/../"+"data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        nose.tools.assert_raises(InvalidTask,BaseTask,
                                 "Task X","taskcmd",dependencies=filePath)

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

    def testTaskError(self):
        self.runner._addTask(CmdTask("taskX","invalid_command asdf"))
        assert self.runner.ERROR == self.runner.run()

    def testSuccess(self):
        self.runner._addTask(CmdTask("taskX",["ls","-1"]))
        self.runner._addTask(CmdTask("taskY",["ls","-1","-a"]))
        assert self.runner.SUCCESS == self.runner.run()

    def testFailure(self):
        self.runner._addTask(CmdTask("taskX",["ls","I dont exist"]))
        assert self.runner.FAILURE == self.runner.run()

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

def func_par(par1,par2,par3=5):
    if par1 == par2 and par3 > 10:
        return True
    else:
        return False


# it is also possible to pass any python callable
class TestPythonTask(ExecuteRunner):
    
    def testPythonTaskSuccess(self):
        def success_sample():return True

        self.runner._addTask(PythonTask("taskX",success_sample))
        assert self.runner.SUCCESS == self.runner.run()

    def testPythonTaskFail(self):
        def fail_sample():return False

        self.runner._addTask(PythonTask("taskX",fail_sample))
        assert self.runner.FAILURE == self.runner.run()

    def testPythonNonFunction(self):
        # any callable should work, not only functions
        class CallMe:
            def __call__(self):
                return False

        self.runner._addTask(PythonTask("taskX",CallMe()))
        assert self.runner.FAILURE == self.runner.run()

    def testFunctionParameters(self):
        self.runner._addTask(PythonTask("taskX",func_par,
                                        args=(2,),kwargs={'par2':2,'par3':25}))
        assert self.runner.SUCCESS == self.runner.run()

    def testFunctionParametersFail(self):
        self.runner._addTask(PythonTask("taskX",func_par,
                                        args=(2,3),kwargs={'par3':25}))
        assert self.runner.FAILURE == self.runner.run()
        
####################

class DumbTask(BaseTask):
    """Dumb Task. do nothing. successful."""
    def execute(self):
        return True

class TestCustomTask(ExecuteRunner):    
    def testCustomSuccess(self):
        self.runner._addTask(DumbTask("dumb",None))
        assert 1 == len(self.runner._tasks)
        assert self.runner.SUCCESS == self.runner.run()

########################
import sys, StringIO

class TestRunnerVerbosityStderr(object):
    def setUp(self):
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stderr.close()
        sys.stderr = self.oldErr

        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

    def raise_something(self):
        sys.stderr.write("this is stderr E\n")
        raise Exception("Hi i am an exception")
        
    def write_on_stderr_success(self):
        sys.stderr.write("this is stderr S\n")
        return True

    def write_on_stderr_fail(self):
        sys.stderr.write("this is stderr F\n")
        return False

    ##### verbosity 0 - STDERR 
    #
    # success - i should not get anything
    def testVerbosity_0_stderr_success(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_success))
        assert runner.SUCCESS == runner.run()
        assert "" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_0_stderr_fail(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_fail))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_0_stderr_error(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]
        
    ##### verbosity 1 - STDERR 
    #
    # success - i should get the stderr
    def testVerbosity_1_stderr_success(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_success))
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_1_stderr_fail(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_fail))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_1_stderr_error(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]


    ##### verbosity 2 - STDERR 
    #
    # success - i should get the stderr
    def testVerbosity_2_stderr_success(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_success))
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_2_stderr_fail(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_fail))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_2_stderr_error(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stderr_success))
        runner._addTask(PythonTask("taskY",self.raise_something))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0], err
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]


class TestRunnerVerbosityStdout(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

    def raise_something(self):
        sys.stdout.write("this is stdout E\n")
        raise Exception("Hi i am an exception")
        
    def write_on_stdout_success(self):
        sys.stdout.write("this is stdout S\n")
        return True

    def write_on_stdout_fail(self):
        sys.stdout.write("this is stdout F\n")
        return False

    ##### verbosity 0 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_0_stdout_success(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_success))
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_0_stdout_fail(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_fail))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()


    # error -  i should get the stdout
    def testVerbosity_0_stdout_error(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 1 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_1_stdout_success(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_success))
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_1_stdout_fail(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_fail))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_1_stdout_error(self):
        runner = Runner(TESTDBM,1)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 2 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_2_stdout_success(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_success))
        assert runner.SUCCESS == runner.run(False)
        assert "this is stdout S\n" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_2_stdout_fail(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_fail))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()\
            , sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_2_stdout_error(self):
        runner = Runner(TESTDBM,2)
        runner._addTask(PythonTask("taskX",self.raise_something))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(TESTDBM,0)
        runner._addTask(PythonTask("taskX",self.write_on_stdout_success))
        runner._addTask(PythonTask("taskY",self.raise_something))
        assert runner.ERROR == runner.run(False)
        sys.__stderr__.write(sys.stdout.getvalue())
        assert "this is stdout E\n" == sys.stdout.getvalue()

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
