import nose.tools

from doit.core import Runner
from doit.core import InvalidTask, BaseTask, CmdTask, PythonTask

class ExecuteRunner(object):
    def setUp(self):
        self.runner = Runner(0)


class TestExecuteTask(ExecuteRunner):
    
    def testAddTask(self):
        self.runner._addTask(CmdTask(["ls","bla bla"],"taskX"))
        self.runner._addTask(CmdTask(["ls","-1"],"taskY"))
        assert 2 == len(self.runner._tasks)

    # 2 tasks can not have the same name
    def testAddTaskSameName(self):
        self.runner._addTask(CmdTask(["ls","bla bla"],"taskX"))
        t = CmdTask(["ls","-1"],"taskX")
        nose.tools.assert_raises(InvalidTask,self.runner._addTask,t)

    def testInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,self.runner._addTask,666)

    def testTaskError(self):
        self.runner._addTask(CmdTask("invalid_command asdf","taskX"))
        assert self.runner.ERROR == self.runner.run()
        assert not self.runner.success

    def testSuccess(self):
        self.runner._addTask(CmdTask(["ls","-1"],"taskX"))
        self.runner._addTask(CmdTask(["ls","-1","-a"],"taskY"))
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

    def testFailure(self):
        self.runner._addTask(CmdTask(["ls","I dont exist"],"taskX"))
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testAnyFailure(self):
        #ok
        self.runner._addTask(CmdTask(["ls"],"taskX"))
        #fail
        self.runner._addTask(CmdTask(["ls","I dont exist"],"taskY"))
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testTuple(self):
        self.runner._addTask(CmdTask(("ls","-1"),"taskX"))
        self.runner._addTask(CmdTask(("ls","-1","-a"),"taskY"))
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success


# it is also possible to pass any python callable
class TestPythonTask(ExecuteRunner):
    
    def testPythonTaskSuccess(self):
        def success_sample():return True

        self.runner._addTask(PythonTask(success_sample,"taskX"))
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

    def testPythonTaskFail(self):
        def fail_sample():return False

        self.runner._addTask(PythonTask(fail_sample,"taskX"))
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testPythonNonFunction(self):
        # any callable should work, not only functions
        class CallMe:
            def __call__(self):
                return False

        self.runner._addTask(PythonTask(CallMe(),"taskX"))
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success


####################

class DumbTask(BaseTask):
    """Dumb Task. do nothing. successful."""
    def execute(self):
        return True

class TestCustomTask(ExecuteRunner):    
    def testCustomSuccess(self):
        self.runner._addTask(DumbTask(None,"dumb"))
        assert 1 == len(self.runner._tasks)
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

########################
import sys, StringIO

class TestRunnerVerbosityStderr(object):
    def setUp(self):
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stderr.close()
        sys.stderr = self.oldErr

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
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stderr_success,"taskX"))
        assert runner.SUCCESS == runner.run()
        assert "" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_0_stderr_fail(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stderr_fail,"taskX"))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_0_stderr_error(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
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
        runner = Runner(1)
        runner._addTask(PythonTask(self.write_on_stderr_success,"taskX"))
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_1_stderr_fail(self):
        runner = Runner(1)
        runner._addTask(PythonTask(self.write_on_stderr_fail,"taskX"))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_1_stderr_error(self):
        runner = Runner(1)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
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
        runner = Runner(2)
        runner._addTask(PythonTask(self.write_on_stderr_success,"taskX"))
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_2_stderr_fail(self):
        runner = Runner(2)
        runner._addTask(PythonTask(self.write_on_stderr_fail,"taskX"))
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_2_stderr_error(self):
        runner = Runner(2)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stderr_success,"taskX"))
        runner._addTask(PythonTask(self.raise_something,"taskY"))
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]


class TestRunnerVerbosityStdout(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

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
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stdout_success,"taskX"))
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_0_stdout_fail(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stdout_fail,"taskX"))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_0_stdout_error(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 1 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_1_stdout_success(self):
        runner = Runner(1)
        runner._addTask(PythonTask(self.write_on_stdout_success,"taskX"))
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_1_stdout_fail(self):
        runner = Runner(1)
        runner._addTask(PythonTask(self.write_on_stdout_fail,"taskX"))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_1_stdout_error(self):
        runner = Runner(1)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 2 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_2_stdout_success(self):
        runner = Runner(2)
        runner._addTask(PythonTask(self.write_on_stdout_success,"taskX"))
        assert runner.SUCCESS == runner.run(False)
        assert "this is stdout S\n" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_2_stdout_fail(self):
        runner = Runner(2)
        runner._addTask(PythonTask(self.write_on_stdout_fail,"taskX"))
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()\
            , sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_2_stdout_error(self):
        runner = Runner(2)
        runner._addTask(PythonTask(self.raise_something,"taskX"))
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(0)
        runner._addTask(PythonTask(self.write_on_stdout_success,"taskX"))
        runner._addTask(PythonTask(self.raise_something,"taskY"))
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


    def testDisplay(self):
        runner = Runner(1)
        runner._addTask(CmdTask(["ls", "-1"],"taskX"))
        runner._addTask(CmdTask(["ls","-a"],"taskY"))
        runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        assert runner._tasks['taskY'].title() == taskTitles[1], taskTitles

