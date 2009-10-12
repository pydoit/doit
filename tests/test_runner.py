import os
import sys

import nose

from doit.dependency import Dependency
from doit.task import Task
from doit.reporter import FakeReporter
from doit import runner

# dependencies file
TESTDB = "testdb"


def tearDownModule():
    if os.path.exists(TESTDB):
        os.remove(TESTDB)


def my_print(*args):
    pass


#FIXME: remove all references to stdout/stderr
class BaseRunner(object):
    def setUp(self):
        self.reporter = FakeReporter()
        if os.path.exists(TESTDB):
            os.remove(TESTDB)


class TestVerbosity(BaseRunner):

    class FakeTask(Task):
        def execute(self, stdout, stderr):
            self.execute_args = {'stdout': stdout,
                                 'stderr': stderr}

    def setUp(self):
        BaseRunner.setUp(self)
        self.fake_task = self.FakeTask('t1', None)

    # 0: capture stdout and stderr
    def test_verbosity0(self):
        runner.run_tasks(TESTDB, [self.fake_task], 0, reporter=self.reporter)
        assert None is self.fake_task.execute_args['stdout']
        assert None is self.fake_task.execute_args['stderr']

    # 1: capture stdout
    def test_verbosity1(self):
        runner.run_tasks(TESTDB, [self.fake_task], 1, reporter=self.reporter)
        assert None is self.fake_task.execute_args['stdout']
        assert sys.stderr is self.fake_task.execute_args['stderr']

    # 2: capture -
    def test_verbosity2(self):
        runner.run_tasks(TESTDB, [self.fake_task], 2, reporter=self.reporter)
        assert sys.stdout is self.fake_task.execute_args['stdout']
        assert sys.stderr is self.fake_task.execute_args['stderr']


class TestRunningTask(BaseRunner):

    def test_success(self):
        tasks = [Task("taskX", [(my_print, ["out a"] )] ),
                 Task("taskY", [(my_print, ["out a"] )] )]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        # only titles are printed.
        assert ('start', tasks[0]) == self.reporter.log[0]
        assert ('start', tasks[1]) == self.reporter.log[1]

    # if task is up to date, it is displayed in a different way.
    def test_successUpToDate(self):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        assert ('start', tasks[0]) == self.reporter.log[0]
        # again
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        reporter2 = FakeReporter()
        result2 = runner.run_tasks(TESTDB, tasks2, reporter=reporter2)
        assert runner.SUCCESS == result2
        assert ('skip', tasks2[0]) == reporter2.log[0]

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self):
        def _fail():
            return False

        tasks = [Task("taskX", [_fail]),
                 Task("taskY", [_fail])]
        result =  runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.FAILURE == result
        assert ('start', tasks[0]) == self.reporter.log[0]
        assert ('fail', tasks[0]) == self.reporter.log[1]
        # second task is not executed
        assert 2 == len(self.reporter.log)


    def test_error(self):
        def _error():
            raise Exception("I am the exception.\n")

        tasks = [Task("taskX", [_error]),
                 Task("taskY", [_error])]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.ERROR == result
        assert ('start', tasks[0]) == self.reporter.log[0]
        assert ('fail', tasks[0]) == self.reporter.log[1]
        # second task is not executed
        assert 2 == len(self.reporter.log)


    # when successful dependencies are updated
    def test_updateDependencies(self):
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
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        d = Dependency(TESTDB)
        # there is only one dependency. targets md5 are not saved.
        assert 1 == len(d._db)

    # when successful and run_once is updated
    def test_successRunOnce(self):
        tasks = [Task("taskX", [my_print], [True], [])]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        d = Dependency(TESTDB)
        assert 1 == len(d._db)


    def test_errorDependency(self):
        tasks = [Task("taskX", [my_print], ["i_dont_exist.xxx"])]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.ERROR == result
        # TODO error on dependency is called before the call reporter start!
        assert ('fail', tasks[0]) == self.reporter.log[0]

    def test_ignoreNonFileDep(self):
        dep = [":taskY"]
        tasks = [Task("taskX", [my_print], dep)]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        d = Dependency(TESTDB)
        assert 0 == len(d._db)


    def test_alwaysExecute(self):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        result = runner.run_tasks(TESTDB, tasks, reporter=self.reporter)
        assert runner.SUCCESS == result
        assert ('start', tasks[0]) == self.reporter.log[0]
        # again
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        reporter2 = FakeReporter()
        result2 = runner.run_tasks(TESTDB, tasks2, alwaysExecute=True,
                                   reporter=reporter2)
        assert runner.SUCCESS == result2
        assert ('start', tasks[0]) == self.reporter.log[0]


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
        result = runner.run_tasks(TESTDB, [t], reporter=self.reporter)
        assert runner.SUCCESS == result
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteOnce(self):
        setup = self.SetupSample()
        t1 = Task("ss", None, [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        result = runner.run_tasks(TESTDB, [t1, t2], reporter=self.reporter)
        assert runner.SUCCESS == result
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteCleanedOnTaskErrors(self):
        setup = self.SetupSample()
        def bad_seed():
            raise Exception("rrrr")
        t1 = Task("ss", [bad_seed], [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        result = runner.run_tasks(TESTDB, [t1, t2], reporter=self.reporter)
        assert runner.ERROR == result
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testSetupError(self):
        # it is same as a task error
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.setup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        result = runner.run_tasks(TESTDB, [t1], reporter=self.reporter)
        assert runner.ERROR == result
        # TODO not checking error is written to output

    def testCleanupError(self):
        # ignore errors...
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.cleanup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        result = runner.run_tasks(TESTDB, [t1], reporter=self.reporter)
        assert runner.SUCCESS == result
        assert ('cleanup_error',) == self.reporter.log[1]


class TestContinue(BaseRunner):
    def test_(self):
        def please_fail():
            return False
        def please_blow():
            raise Exception("bum")
        def ok():
            pass
        tasks = [Task("task1", [(please_fail,)] ),
                 Task("task2", [(please_blow,)] ),
                 Task("task3", [(ok,)])]
        result = runner.run_tasks(TESTDB, tasks, continue_=True,
                                  reporter=self.reporter)
        assert runner.ERROR == result
        assert ('start', tasks[0]) == self.reporter.log[0]
        assert ('fail', tasks[0]) == self.reporter.log[1]
        assert ('start', tasks[1]) == self.reporter.log[2]
        assert ('fail', tasks[1]) == self.reporter.log[3]
        assert ('start', tasks[2]) == self.reporter.log[4]
        assert 5 == len(self.reporter.log)


class TestSystemExit(BaseRunner):

    # SystemExit runner should interfere with SystemExit
    def testRaises(self):
        def i_raise():
            raise SystemExit()
        t1 = Task("x", [i_raise])
        nose.tools.assert_raises(SystemExit, runner.run_tasks, TESTDB, [t1],
                                 reporter=self.reporter)
