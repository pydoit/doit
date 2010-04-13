import os

import py.test

from doit.dependency import Dependency
from doit.task import Task
from doit.reporter import FakeReporter
from doit import runner

# dependencies file
TESTDB = "testdb"


def my_print(*args):
    pass


def pytest_funcarg__reporter(request):
    def remove_testdb(void):
        if os.path.exists(TESTDB):
            os.remove(TESTDB)
    def create_fake_reporter():
        remove_testdb(None)
        return FakeReporter()
    return request.cached_setup(
        setup=create_fake_reporter,
        teardown=remove_testdb,
        scope="function")


class TestRunningTask(object):

    def test_success(self, reporter):
        tasks = [Task("taskX", [(my_print, ["out a"] )] ),
                 Task("taskY", [(my_print, ["out a"] )] )]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('success', tasks[0]) == reporter.log.pop(0)
        assert ('start', tasks[1]) == reporter.log.pop(0)
        assert ('execute', tasks[1]) == reporter.log.pop(0)
        assert ('success', tasks[1]) == reporter.log.pop(0)

    # if task is up to date, it is displayed in a different way.
    def test_successUpToDate(self, reporter):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        # again
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        reporter2 = FakeReporter()
        my_runner2 = runner.Runner(TESTDB, reporter2)
        my_runner2.run_tasks(tasks2)
        assert runner.SUCCESS == my_runner2.finish()
        assert ('start', tasks2[0]) == reporter2.log.pop(0)
        assert ('up-to-date', tasks2[0]) == reporter2.log.pop(0)

    def test_ignore(self, reporter):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        dependencyManager = Dependency(TESTDB)
        dependencyManager.ignore(tasks[0])
        dependencyManager.close()
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('ignore', tasks[0]) == reporter.log.pop(0), reporter.log

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self, reporter):
        def _fail():
            return False

        tasks = [Task("taskX", [_fail]),
                 Task("taskY", [_fail])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.FAILURE == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    def test_error(self, reporter):
        def _error():
            raise Exception("I am the exception.\n")

        tasks = [Task("taskX", [_error]),
                 Task("taskY", [_error])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.ERROR == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    # when successful dependencies are updated
    def test_updateDependencies(self, reporter):
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
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        d = Dependency(TESTDB)
        # there is only one dependency. targets md5 are not saved.
        assert 1 == len(d._db)

    # when successful and run_once is updated
    def test_successRunOnce(self, reporter):
        tasks = [Task("taskX", [my_print], [True], [])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        d = Dependency(TESTDB)
        assert 1 == len(d._db)


    def test_errorDependency(self, reporter):
        tasks = [Task("taskX", [my_print], ["i_dont_exist.xxx"])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.ERROR == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        assert 0 == len(reporter.log)

    def test_ignoreNonFileDep(self, reporter):
        dep = [":taskY"]
        tasks = [Task("taskX", [my_print], dep)]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        d = Dependency(TESTDB)
        assert 0 == len(d._db)


    def test_alwaysExecute(self, reporter):
        tasks = [Task("taskX", [my_print], dependencies=[__file__])]
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks(tasks)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        # again
        tasks2 = [Task("taskX", [my_print], dependencies=[__file__])]
        reporter2 = FakeReporter()
        my_runner2 = runner.Runner(TESTDB, reporter2, always_execute=True)
        my_runner2.run_tasks(tasks2)
        assert runner.SUCCESS == my_runner2.finish()
        assert ('start', tasks2[0]) == reporter2.log.pop(0)
        assert ('execute', tasks2[0]) == reporter2.log.pop(0)


    def test_resultDependency(self, reporter):
        def ok(): return "ok"
        t1 = Task("t1", [(ok,)])
        t2 = Task("t2", [(ok,)], ['?t1'])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1, t2])
        my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)
        # again
        my_runner2 = runner.Runner(TESTDB, reporter)
        my_runner2.run_tasks([t1, t2])
        my_runner2.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('up-to-date', t2) == reporter.log.pop(0)
        # change t1, t2 executed again
        def ok2(): return "different"
        t1B = Task("t1", [(ok2,)])
        my_runner3 = runner.Runner(TESTDB, reporter)
        my_runner3.run_tasks([t1B, t2])
        my_runner3.finish()
        assert ('start', t1B) == reporter.log.pop(0)
        assert ('execute', t1B) == reporter.log.pop(0)
        assert ('success', t1B) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)

    def test_getargs_ok(self, reporter):
        def ok(): return {'x':1}
        def check_x(my_x): return my_x == 1
        t1 = Task('t1', [(ok,)])
        t2 = Task('t2', [(check_x,)], getargs={'my_x':'t1.x'})
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1,t2])
        my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)

    def test_getargs_fail(self, reporter):
        # invalid getargs. Exception wil be raised and task will fail
        def check_x(my_x): return True
        t2 = Task('t2', [(check_x,)], getargs={'my_x':'t1.x'})
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t2])
        my_runner.finish()
        assert ('start', t2) == reporter.log.pop(0)
        assert ('fail', t2) == reporter.log.pop(0)


class TestTaskSetup(object):

    class SetupSample(object):
        def __init__(self):
            self.executed = 0
            self.cleaned = 0

        def setup(self):
            self.executed += 1

        def cleanup(self):
            self.cleaned += 1

    def testExecuted(self, reporter):
        setup = self.SetupSample()
        t = Task("ss", None, [], [], [setup])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t])
        assert runner.SUCCESS == my_runner.finish()
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteOnce(self, reporter):
        setup = self.SetupSample()
        t1 = Task("ss", None, [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1, t2])
        assert runner.SUCCESS == my_runner.finish()
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testExecuteCleanedOnTaskErrors(self, reporter):
        setup = self.SetupSample()
        def bad_seed():
            raise Exception("rrrr")
        t1 = Task("ss", [bad_seed], [], [], [setup])
        t2 = Task("ss2", None, [], [], [setup])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1, t2])
        assert runner.ERROR == my_runner.finish()
        assert 1 == setup.executed
        assert 1 == setup.cleaned

    def testSetupError(self, reporter):
        # it is same as a task error
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.setup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1])
        assert runner.ERROR == my_runner.finish()
        # TODO not checking error is written to output

    def testCleanupError(self, reporter):
        # ignore errors...
        def raise_something():
            raise Exception('xxx')
        setup = self.SetupSample()
        setup.cleanup = raise_something
        t1 = Task('t1', None, [], [], [setup])
        my_runner = runner.Runner(TESTDB, reporter)
        my_runner.run_tasks([t1])
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('cleanup_error',) == reporter.log.pop(0)


class TestContinue(object):
    def test_(self, reporter):
        def please_fail():
            return False
        def please_blow():
            raise Exception("bum")
        def ok():
            pass
        tasks = [Task("task1", [(please_fail,)] ),
                 Task("task2", [(please_blow,)] ),
                 Task("task3", [(ok,)])]
        my_runner = runner.Runner(TESTDB, reporter, continue_=True)
        my_runner.run_tasks(tasks)
        assert runner.ERROR == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        assert ('start', tasks[1]) == reporter.log.pop(0)
        assert ('execute', tasks[1]) == reporter.log.pop(0)
        assert ('fail', tasks[1]) == reporter.log.pop(0)
        assert ('start', tasks[2]) == reporter.log.pop(0)
        assert ('execute', tasks[2]) == reporter.log.pop(0)
        assert ('success', tasks[2]) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


class TestSystemExit(object):
    # SystemExit runner should not interfere with SystemExit
    def testRaises(self, reporter):
        def i_raise():
            raise SystemExit()
        t1 = Task("x", [i_raise])
        my_runner = runner.Runner(TESTDB, reporter)
        py.test.raises(SystemExit, my_runner.run_tasks, [t1])
