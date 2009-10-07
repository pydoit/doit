import os
import sys, StringIO

import nose

from doit.dependency import Dependency
from doit.task import Task
from doit import runner

# dependencies file
TESTDB = "testdb"


def tearDownModule():
    if os.path.exists(TESTDB):
        os.remove(TESTDB)


def my_print(out="",err=""):
    sys.stdout.write(out)
    sys.stderr.write(err)
    return True

#FIXME: remove all references to stdout/stderr
class BaseRunner(object):
    def setUp(self):
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()
        if os.path.exists(TESTDB):
            os.remove(TESTDB)

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut
        sys.stderr.close()
        sys.stderr = self.oldErr


class TestVerbosity(BaseRunner):

    class FakeTask(Task):
        def execute(self, capture_stdout = False, capture_stderr = False):
            self.execute_args = {'capture_stdout': capture_stdout,
                                 'capture_stderr': capture_stderr}

    def setUp(self):
        BaseRunner.setUp(self)
        self.fake_task = self.FakeTask('t1', None)

    # 0: capture stdout and stderr
    def test_verbosity0(self):
        runner.run_tasks(TESTDB, [self.fake_task], 0)
        assert self.fake_task.execute_args['capture_stdout']
        assert self.fake_task.execute_args['capture_stderr']

    # 1: capture stdout
    def test_verbosity1(self):
        runner.run_tasks(TESTDB, [self.fake_task], 1)
        assert self.fake_task.execute_args['capture_stdout']
        assert not self.fake_task.execute_args['capture_stderr']

    # 2: capture -
    def test_verbosity2(self):
        runner.run_tasks(TESTDB, [self.fake_task], 2)
        assert not self.fake_task.execute_args['capture_stdout']
        assert not self.fake_task.execute_args['capture_stderr']


class TestRunningTask(BaseRunner):

    def test_successOutput(self):
        tasks = [Task("taskX", [(my_print, ["out a"] )] ),
                 Task("taskY", [(my_print, ["out a"] )] )]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        # only titles are printed.
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        assert tasks[1].title() == taskTitles[1], taskTitles

    def test_successVerboseOutput(self):
        tasks = [Task("taskX", [(my_print, ["stdout here.\n"])] )]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 2)
        output = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == output[0], output
        # captured output is displayed
        assert "stdout here." == output[1], output
        # nothing more (but the empty string)
        assert 3 == len(output)

    # if task is up to date, it is displayed in a different way.
    def test_successUpToDate(self):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        # again
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        sys.stdout = StringIO.StringIO()
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks2, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert "--- " + tasks2[0].title() == taskTitles[0]

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self):
        def write_and_fail():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            return False

        tasks = [Task("taskX", [write_and_fail]),
                 Task("taskY", [write_and_fail])]
        assert runner.FAILURE == runner.run_tasks(TESTDB, tasks, 0)
        output = sys.stdout.getvalue().split('\n')
        errput = sys.stderr.getvalue().strip().split('\n')
        assert tasks[0].title() == output[0], output
        # nothing more (but the empty string)
        assert 2 == len(output)
        # captured output is displayed on stderr
        assert "stdout here." == errput[-3], errput
        assert "stderr here." == errput[-1]
        # final failed message
        assert "TaskFailed: taskX" == errput[1], errput


    def test_errorOutput(self):
        def write_and_error():
            sys.stdout.write("stdout here.\n")
            sys.stderr.write("stderr here.\n")
            raise Exception("I am the exception.\n")

        tasks = [Task("taskX", [write_and_error]),
                 Task("taskY", [write_and_error])]
        assert runner.ERROR == runner.run_tasks(TESTDB, tasks, 0)
        output = sys.stdout.getvalue().split('\n')
        errput = sys.stderr.getvalue().strip().split('\n')
        assert tasks[0].title() == output[0], output
        # captured output is displayed on stderr
        assert "stdout here." == errput[-3], errput
        # nothing more (but the empty string)
        assert 2 == len(output)
        # stderr
        assert "stderr here." ==  errput[-1]
        # final failed message
        assert "TaskError: taskX" == errput[1], errput
        assert 'Exception: I am the exception.' == errput[-6], errput



    # when successful dependencies are updated
    def test_successDependencies(self):
        filePath = os.path.join(os.path.dirname(__file__),"data/dependency1")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        dependencies = [filePath]

        filePath = os.path.join(os.path.dirname(__file__),"data/target")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        tasks = [Task("taskX", [my_print], dependencies, targets)]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        d = Dependency(TESTDB)
        # there is only one dependency. targets md5 are not saved.
        assert 1 == len(d._db)

    # when successful and run_once is updated
    def test_successRunOnce(self):
        tasks = [Task("taskX", [my_print], [True], [])]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        d = Dependency(TESTDB)
        assert 1 == len(d._db)


    def test_errorDependency(self):
        tasks = [Task("taskX", [my_print], ["i_dont_exist.xxx"])]
        assert runner.ERROR == runner.run_tasks(TESTDB, tasks, 1)
        # only titles are printed.
        errput = sys.stderr.getvalue().split('\n')
        name = tasks[0].name
        assert "ERROR checking dependencies" == errput[2], errput


    def test_ignoreNonFileDep(self):
        dep = [":taskY"]
        tasks = [Task("taskX", [my_print], dep)]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        d = Dependency(TESTDB)
        assert 0 == len(d._db)


    def test_alwaysExecute(self):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks, 1)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]
        # again
        sys.stdout = StringIO.StringIO()
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        assert runner.SUCCESS == runner.run_tasks(TESTDB, tasks2, 1,True)
        taskTitles = sys.stdout.getvalue().split('\n')
        assert tasks[0].title() == taskTitles[0]


class TestTaskSetup(BaseRunner):

    class SetupSample(object):
        def __init__(self):
            self.executed = 0
            self.cleaned = 0

        def setup(self):
            self.executed += 1

        def cleanup(self):
            self.cleaned += 1

    def testExecuted(self):
        setup = self.SetupSample()
        t = Task("ss", None, [], [], [setup])
        assert runner.SUCCESS == runner.run_tasks(TESTDB, [t])
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteOnce(self):
        setup = self.SetupSample()
        t1 = Task("ss", None, [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        assert runner.SUCCESS == runner.run_tasks(TESTDB, [t1, t2])
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteCleanedOnTaskErrors(self):
        setup = self.SetupSample()
        def bad_seed():
            raise Exception("rrrr")
        t1 = Task("ss", [bad_seed], [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        assert runner.ERROR == runner.run_tasks(TESTDB, [t1, t2])
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testSetupError(self):
        # it is same as a task error
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.setup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        assert runner.ERROR == runner.run_tasks(TESTDB, [t1])
        # TODO not checking error is written to output

    def testCleanupError(self):
        # ignore errors...
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.cleanup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        assert runner.SUCCESS == runner.run_tasks(TESTDB, [t1])


class TestSystemExit(BaseRunner):

    # SystemExit runner should interfere with SystemExit
    def testRaises(self):
        def i_raise():
            raise SystemExit()
        t1 = Task("x", [i_raise])
        nose.tools.assert_raises(SystemExit, runner.run_tasks, TESTDB, [t1])
