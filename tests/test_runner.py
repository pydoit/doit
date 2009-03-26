import os
import sys, StringIO

import nose.tools

from doit.dependency import Dependency
from doit.task import InvalidTask, BaseTask, PythonTask
from doit.runner import Runner

# dependencies file
TESTDBM = "testdbm"

def my_print(out="",err=""):
    sys.stdout.write(out)
    sys.stderr.write(err)
    return True

class TestVerbosity(object):
 
    # 0: capture stdout and stderr
    def test_verbosity0(self):
        Runner(TESTDBM,0)
        assert BaseTask.CAPTURE_OUT
        assert BaseTask.CAPTURE_ERR

    # 1: capture stdout
    def test_verbosity1(self):
        Runner(TESTDBM,1)
        assert BaseTask.CAPTURE_OUT
        assert not BaseTask.CAPTURE_ERR

    # 2: capture -
    def test_verbosity2(self):
        Runner(TESTDBM,2)
        assert not BaseTask.CAPTURE_OUT
        assert not BaseTask.CAPTURE_ERR



class TestAddTask(object):

    def setUp(self):
        self.runner = Runner(TESTDBM,0)
    
    def testadd_task(self):
        self.runner.add_task(PythonTask("taskX",my_print))
        self.runner.add_task(PythonTask("taskY",my_print))
        assert 2 == len(self.runner._tasks)

    # 2 tasks can not have the same name
    def testadd_taskSameName(self):
        self.runner.add_task(PythonTask("taskX",my_print))
        t = PythonTask("taskX",my_print)
        nose.tools.assert_raises(InvalidTask,self.runner.add_task,t)

    def test_addInvalidTask(self):
        nose.tools.assert_raises(InvalidTask,self.runner.add_task,666)




class TestRunningTask(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut
        sys.stderr.close()
        sys.stderr = self.oldErr
        if os.path.exists(TESTDBM):
            os.remove(TESTDBM)

    def test_successOutput(self):
        runner = Runner(TESTDBM,1)
        runner.add_task(PythonTask("taskX",my_print,args=["out a"]))
        runner.add_task(PythonTask("taskY",my_print,args=["out a"]))
        assert runner.SUCCESS == runner.run()
        # only titles are printed.
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        assert runner._tasks['taskY'].title() == taskTitles[1], taskTitles

    def test_successVerboseOutput(self):
        runner = Runner(TESTDBM,2)
        task = PythonTask("taskX",my_print,args=["stdout here.\n"])
        runner.add_task(task)
        assert runner.SUCCESS == runner.run()
        output = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1], output
        # nothing more (but the empty string)
        assert 3 == len(output)

    # if task is up to date, it is displayed in a different way.
    def test_successUpToDate(self):
        runner = Runner(TESTDBM,1)
        runner.add_task(PythonTask("taskX",my_print,dependencies=[__file__]))
        assert runner.SUCCESS == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        # again
        sys.stdout = StringIO.StringIO()
        runner2 = Runner(TESTDBM,1)
        runner2.add_task(PythonTask("taskX",my_print,dependencies=[__file__]))
        assert runner2.SUCCESS == runner2.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert "--- " +runner2._tasks['taskX'].title() == taskTitles[0]

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self):
        def write_and_fail():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            return False

        runner = Runner(TESTDBM,0)
        runner.add_task(PythonTask("taskX",write_and_fail))
        runner.add_task(PythonTask("taskY",write_and_fail))
        assert runner.FAILURE == runner.run()
        output = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1]
        assert "stderr here.\n" == sys.stderr.getvalue()
        # final failed message
        assert "Task failed" == output[2]
        # nothing more (but the empty string)
        assert 4 == len(output)


    def test_errorOutput(self):
        def write_and_error():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            raise Exception("I am the exception.\n")

        runner = Runner(TESTDBM,0)
        runner.add_task(PythonTask("taskX",write_and_error))
        runner.add_task(PythonTask("taskY",write_and_error))
        assert runner.ERROR == runner.run()
        output = sys.stdout.getvalue().split('\n')
        errput = sys.stderr.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1]
        # final failed message
        assert "Task error" == output[2], output
        # nothing more (but the empty string)
        assert 4 == len(output)
        # stderr
        assert "stderr here." ==  errput[0]
        assert 'Exception: I am the exception.' == errput[-3]



    # when successful dependencies are updated
    def test_successDependencies(self):
        filePath = os.path.abspath(__file__+"/../data/dependency1")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        dependencies = [filePath]

        filePath = os.path.abspath(__file__+"/../data/target")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        runner = Runner(TESTDBM,1)
        runner.add_task(PythonTask("taskX",my_print,dependencies,targets))
        assert runner.SUCCESS == runner.run()
        # only titles are printed.
        d = Dependency(TESTDBM)
        assert 2 == len(d._db)


    def test_errorDependency(self):
        runner = Runner(TESTDBM,1)
        runner.add_task(PythonTask("taskX",my_print,["i_dont_exist.xxx"]))
        assert runner.ERROR == runner.run()
        # only titles are printed.
        output = sys.stdout.getvalue().split('\n')
        title = runner._tasks['taskX'].title()
        assert "" == output[0], output
        assert "ERROR checking dependencies for: %s"% title == output[1]


    def test_alwaysExecute(self):
        runner = Runner(TESTDBM,1)
        runner.add_task(PythonTask("taskX",my_print,dependencies=[__file__]))
        assert runner.SUCCESS == runner.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner._tasks['taskX'].title() == taskTitles[0]
        # again
        sys.stdout = StringIO.StringIO()
        runner2 = Runner(TESTDBM,1,True)
        runner2.add_task(PythonTask("taskX",my_print,dependencies=[__file__]))
        assert runner2.SUCCESS == runner2.run()
        taskTitles = sys.stdout.getvalue().split('\n')
        assert runner2._tasks['taskX'].title() == taskTitles[0]
