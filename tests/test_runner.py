import os
import sys, StringIO

import nose

from doit.dependency import Dependency
from doit.task import BaseTask, PythonTask, GroupTask
from doit import runner

# dependencies file
TESTDBM = "testdbm"

def my_print(out="",err=""):
    sys.stdout.write(out)
    sys.stderr.write(err)
    return True

class TestVerbosity(object):

    # 0: capture stdout and stderr
    def test_verbosity0(self):
        runner.run_tasks(TESTDBM, [], 0)
        assert BaseTask.CAPTURE_OUT
        assert BaseTask.CAPTURE_ERR

    # 1: capture stdout
    def test_verbosity1(self):
        runner.run_tasks(TESTDBM, [], 1)
        assert BaseTask.CAPTURE_OUT
        assert not BaseTask.CAPTURE_ERR

    # 2: capture -
    def test_verbosity2(self):
        runner.run_tasks(TESTDBM, [], 2)
        assert not BaseTask.CAPTURE_OUT
        assert not BaseTask.CAPTURE_ERR



class BaseRunner(object):
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

class TestRunningTask(BaseRunner):

    def test_successOutput(self):
        tasks = [PythonTask("taskX",my_print,args=["out a"]),
                 PythonTask("taskY",my_print,args=["out a"])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        # only titles are printed.
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        assert tasks[1].title() == taskTitles[1], taskTitles

    def test_successVerboseOutput(self):
        tasks = [PythonTask("taskX",my_print,args=["stdout here.\n"])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 2)
        output = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1], output
        # nothing more (but the empty string)
        assert 3 == len(output)

    # if task is up to date, it is displayed in a different way.
    def test_successUpToDate(self):
        tasks = [PythonTask("taskX",my_print,dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        # again
        tasks2 = [PythonTask("taskX",my_print,dependencies=[__file__])]
        sys.stdout = StringIO.StringIO()
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks2, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert "--- " + tasks2[0].title() == taskTitles[0]

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self):
        def write_and_fail():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            return False

        tasks = [PythonTask("taskX",write_and_fail),
                 PythonTask("taskY",write_and_fail)]
        assert runner.FAILURE == runner.run_tasks(TESTDBM, tasks, 0)
        output = sys.stdout.getvalue().split('\n')
        errput = sys.stderr.getvalue().split('\n')
        assert tasks[0].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1]
        assert "stderr here." == errput[0]
        # final failed message
        assert "Task failed => taskX" == errput[2], errput
        # nothing more (but the empty string)
        assert 3 == len(output)


    def test_errorOutput(self):
        def write_and_error():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            raise Exception("I am the exception.\n")

        tasks = [PythonTask("taskX",write_and_error),
                 PythonTask("taskY",write_and_error)]
        assert runner.ERROR == runner.run_tasks(TESTDBM, tasks, 0)
        output = sys.stdout.getvalue().split('\n')
        errput = sys.stderr.getvalue().split('\n')
        assert tasks[0].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1]
        # nothing more (but the empty string)
        assert 3 == len(output)
        # stderr
        assert "stderr here." ==  errput[0]
        # final failed message
        assert "Task error => taskX" == errput[2], errput
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

        tasks = [PythonTask("taskX",my_print,dependencies,targets)]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        d = Dependency(TESTDBM)
        # there is only one dependency. targets md5 are not saved.
        assert 1 == len(d._db)

    # when successful and run_once is updated
    def test_successRunOnce(self):
        tasks = [PythonTask("taskX",my_print,[True],[])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        d = Dependency(TESTDBM)
        assert 1 == len(d._db)


    def test_errorDependency(self):
        tasks = [PythonTask("taskX",my_print,["i_dont_exist.xxx"])]
        assert runner.ERROR == runner.run_tasks(TESTDBM, tasks, 1)
        # only titles are printed.
        output = sys.stdout.getvalue().split('\n')
        title = tasks[0].title()
        assert "" == output[0], output
        assert "ERROR checking dependencies for: %s"% title == output[1]


    def test_ignoreNonFileDep(self):
        DIR_DEP = os.path.abspath(__file__+"/../folder_dep/")+'/'
        dep = [DIR_DEP, ":taskY"]
        tasks = [PythonTask("taskX",my_print,dep)]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        d = Dependency(TESTDBM)
        assert 0 == len(d._db)
        if os.path.exists(DIR_DEP): os.removedirs(DIR_DEP)


    def test_alwaysExecute(self):
        tasks = [PythonTask("taskX",my_print,dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        # again
        sys.stdout = StringIO.StringIO()
        tasks2 = [PythonTask("taskX",my_print,dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks2, 1,True)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]


    def test_createFolderDependency(self):
        def rm_dir():
            if os.path.exists(DIR_DEP):
                os.removedirs(DIR_DEP)

        DIR_DEP = os.path.abspath(__file__+"/../parent/child/")+'/'
        rm_dir()
        tasks = [PythonTask("taskX",my_print,dependencies=[DIR_DEP])]
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, tasks, 1)
        assert os.path.exists(DIR_DEP)
        rm_dir()


class TestTaskSetup(BaseRunner):

    class SetupSample(object):
        def __init__(self):
            self.executed = 0
            self.cleaned = 0

        def setup(self):
            self.executed += 1

        def cleanup(self):
            self.cleaned += 1

    #FIXME test a setup attribute is required. and cleanup is optional
    #TODO check errors on setup and cleanup

    def testExecuted(self):
        setup = self.SetupSample()
        t = GroupTask("ss", None, [], [], setup)
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, [t])
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteOnce(self):
        setup = self.SetupSample()
        t1 = GroupTask("ss", None, [], [], setup)
        t2 = GroupTask("ss2", None, [], [], setup)
        assert runner.SUCCESS == runner.run_tasks(TESTDBM, [t1, t2])
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteCleanedOnTaskErrors(self):
        setup = self.SetupSample()
        def bad_seed():
            raise Exception("rrrr")
        t1 = PythonTask("ss", bad_seed, [], [], setup)
        t2 = GroupTask("ss2", None, [], [], setup)
        assert runner.ERROR == runner.run_tasks(TESTDBM, [t1, t2])
        assert 1 == setup.executed
        assert 1 == setup.cleaned


class TestSystemExit(BaseRunner):

    # SystemExit runner should interfere with SystemExit
    def testRaises(self):
        def i_raise():
            raise SystemExit()
        t1 = PythonTask("x",i_raise)
        nose.tools.assert_raises(SystemExit, runner.run_tasks, TESTDBM, [t1])
