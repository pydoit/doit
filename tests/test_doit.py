import nose.tools

from doit import Runner
from doit.core import InvalidTask, BaseTask, Loader

class ExecuteRunner(object):
    def setUp(self):
        self.runner = Runner(0)


class TestExecuteTask(ExecuteRunner):
    
    def testAddTask(self):
        self.runner.addTask(["ls","bla bla"])
        self.runner.addTask(["ls","-1"])
        assert 2 == len(self.runner._tasks)

    def testInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,self.runner.addTask,666)

    def testTaskError(self):
        self.runner.addTask("invalid_command asdf")
        assert self.runner.ERROR == self.runner.run()
        assert not self.runner.success

    def testSuccess(self):
        self.runner.addTask(["ls","-1"])
        self.runner.addTask(["ls","-1","-a"])
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

    def testFailure(self):
        self.runner.addTask(["ls","I dont exist"])
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testAnyFailure(self):
        #ok
        self.runner.addTask(["ls"])
        #fail
        self.runner.addTask(["ls","I dont exist"])
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testTuple(self):
        self.runner.addTask(("ls","-1"))
        self.runner.addTask(("ls","-1","-a"))
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

# you can pass a cmd as a string to addTask.
class TestStringTask(ExecuteRunner):
    
    def testStringTaskSuccess(self):
        self.runner.addTask("ls -1 -a")
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success
        
    def testStringTaskFailure(self):
        self.runner.addTask("ls i_dont_exist")
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

# it is also possible to pass any python callable
class TestPythonTask(ExecuteRunner):
    
    def testPythonTaskSuccess(self):
        def success_sample():return True

        self.runner.addTask(success_sample)
        assert self.runner.SUCCESS == self.runner.run()
        assert self.runner.success

    def testPythonTaskFail(self):
        def fail_sample():return False

        self.runner.addTask(fail_sample)
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

    def testPythonNonFunction(self):
        # any callable should work, not only functions
        class CallMe:
            def __call__(self):
                return False

        self.runner.addTask(CallMe())
        assert self.runner.FAILURE == self.runner.run()
        assert not self.runner.success

###############
def genSample():
    cmds = ["ls","ls -1"]
    for c in cmds:
        yield c

class TestGeneratorTask(ExecuteRunner):
    
    def testGenerator(self):
        self.runner.addTask(genSample())
        assert 2 == len(self.runner._tasks)

##################

import os,inspect
class TestLoader():
    def setUp(self):
        # this test can be executed from any path
        self.fileName = os.path.abspath(__file__+"/../sample.py")

    def testImport(self):
        loaded = Loader(self.fileName)
        assert inspect.ismodule(loaded.module)

    def testGetTaskGenerators(self):
        loaded = Loader(self.fileName)
        funcNames =  [f.name for f in loaded.getTaskGenerators()]
        expected = ["nose","checker"]
        assert expected == funcNames

    def testRelativeImport(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(__file__+"/../.."))
        self.fileName = "tests/sample.py"
        self.testImport()

#############

class DumbTask(BaseTask):
    """Dumb Task. do nothing. successful."""
    def execute(self):
        return True

class TestCustomTask(ExecuteRunner):    
    def testCustomSuccess(self):
        self.runner.addTask(DumbTask(None))
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
        runner.addTask(self.write_on_stderr_success)
        assert runner.SUCCESS == runner.run()
        assert "" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_0_stderr_fail(self):
        runner = Runner(0)
        runner.addTask(self.write_on_stderr_fail)
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_0_stderr_error(self):
        runner = Runner(0)
        runner.addTask(self.raise_something)
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
        runner.addTask(self.write_on_stderr_success)
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_1_stderr_fail(self):
        runner = Runner(1)
        runner.addTask(self.write_on_stderr_fail)
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_1_stderr_error(self):
        runner = Runner(1)
        runner.addTask(self.raise_something)
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
        runner.addTask(self.write_on_stderr_success)
        assert runner.SUCCESS == runner.run()
        assert "this is stderr S\n" == sys.stderr.getvalue()

    # failure - i should get the stderr
    def testVerbosity_2_stderr_fail(self):
        runner = Runner(2)
        runner.addTask(self.write_on_stderr_fail)
        assert runner.FAILURE == runner.run()
        assert "this is stderr F\n" == sys.stderr.getvalue()

    # error -  i should get the stderr
    # and the traceback of the error.
    def testVerbosity_2_stderr_error(self):
        runner = Runner(2)
        runner.addTask(self.raise_something)
        assert runner.ERROR == runner.run()
        # stderr by line
        err = sys.stderr.getvalue().split('\n')
        assert "this is stderr E" == err[0]
        # ignore traceback, compare just exception message
        assert "Exception: Hi i am an exception" == err[-2]

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(0)
        runner.addTask(self.write_on_stderr_success)
        runner.addTask(self.raise_something)
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
        runner.addTask(self.write_on_stdout_success)
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_0_stdout_fail(self):
        runner = Runner(0)
        runner.addTask(self.write_on_stdout_fail)
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_0_stdout_error(self):
        runner = Runner(0)
        runner.addTask(self.raise_something)
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 1 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_1_stdout_success(self):
        runner = Runner(1)
        runner.addTask(self.write_on_stdout_success)
        assert runner.SUCCESS == runner.run(False)
        assert "" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_1_stdout_fail(self):
        runner = Runner(1)
        runner.addTask(self.write_on_stdout_fail)
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_1_stdout_error(self):
        runner = Runner(1)
        runner.addTask(self.raise_something)
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    ##### verbosity 2 - STDOUT 
    #
    # success - i should not get anything
    def testVerbosity_2_stdout_success(self):
        runner = Runner(2)
        runner.addTask(self.write_on_stdout_success)
        assert runner.SUCCESS == runner.run(False)
        assert "this is stdout S\n" == sys.stdout.getvalue()

    # failure - i should get the stdout
    def testVerbosity_2_stdout_fail(self):
        runner = Runner(2)
        runner.addTask(self.write_on_stdout_fail)
        assert runner.FAILURE == runner.run(False)
        assert "this is stdout F\nTask failed\n" == sys.stdout.getvalue()\
            , sys.stdout.getvalue()

    # error -  i should get the stdout
    def testVerbosity_2_stdout_error(self):
        runner = Runner(2)
        runner.addTask(self.raise_something)
        assert runner.ERROR == runner.run(False)
        assert "this is stdout E\n" == sys.stdout.getvalue()

    # captured streams should be show only for the tasks that failed
    def testVerboseOnlyErrorTask(self):
        runner = Runner(0)
        runner.addTask(self.write_on_stdout_success)
        runner.addTask(self.raise_something)
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
        runner.addTask("ls -1")
        runner.addTask("ls -a")
        runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks[0].title() == taskTitles[0]
        assert runner._tasks[1].title() == taskTitles[1]

