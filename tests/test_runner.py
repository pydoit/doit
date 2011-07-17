import os
from multiprocessing import Queue

import pytest
from mock import Mock

from doit.dependency import Dependency
from doit.task import Task
from doit.control import TaskControl
from doit import runner


# sample actions
def my_print(*args):
    pass
def _fail():
    return False
def _error():
    raise Exception("I am the exception.\n")
def _exit():
    raise SystemExit()


class FakeReporter(object):
    """Just log everything in internal attribute - used on tests"""
    def __init__(self, outstream=None, options=None):
        self.log = []

    def get_status(self, task):
        self.log.append(('start', task))

    def execute_task(self, task):
        self.log.append(('execute', task))

    def add_failure(self, task, exception):
        self.log.append(('fail', task))

    def add_success(self, task):
        self.log.append(('success', task))

    def skip_uptodate(self, task):
        self.log.append(('up-to-date', task))

    def skip_ignore(self, task):
        self.log.append(('ignore', task))

    def cleanup_error(self, exception):
        self.log.append(('cleanup_error',))

    def runtime_error(self, msg):
        self.log.append(('runtime_error',))

    def teardown_task(self, task):
        self.log.append(('teardown', task))

    def complete_run(self):
        pass


def pytest_funcarg__reporter(request):
    def create_fake_reporter():
        return FakeReporter()
    return request.cached_setup(
        setup=create_fake_reporter,
        scope="function")


class TestRunner(object):
    def testInit(self, reporter, depfile):
        my_runner = runner.Runner(depfile.name, reporter)
        assert False == my_runner._stop_running
        assert runner.SUCCESS == my_runner.final_result


class TestRunner_SelectTask(object):
    def test_ready(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(depfile.name, reporter)
        assert True == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_DependencyError(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )],
                  file_dep=["i_dont_exist"])
        my_runner = runner.Runner(depfile.name, reporter)
        assert False == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_upToDate(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )], file_dep=[__file__])
        my_runner = runner.Runner(depfile.name, reporter)
        my_runner.dependency_manager.save_success(t1)
        assert False == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert ('up-to-date', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_ignore(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(depfile.name, reporter)
        my_runner.dependency_manager.ignore(t1)
        assert False == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert ('ignore', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_alwaysExecute(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(depfile.name, reporter, always_execute=True)
        my_runner.dependency_manager.ignore(t1)
        assert True == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_noSetup_ok(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(depfile.name, reporter)
        assert True == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_withSetup(self, reporter, depfile):
        t1 = Task("taskX", [(my_print, ["out a"] )], setup=["taskY"])
        my_runner = runner.Runner(depfile.name, reporter)
        # defer execution
        assert False == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log
        # trying to select again
        assert True == my_runner.select_task(t1)
        assert not reporter.log


    def test_getargs_ok(self, reporter, depfile):
        def ok(): return {'x':1}
        def check_x(my_x): return my_x == 1
        t1 = Task('t1', [(ok,)])
        t2 = Task('t2', [(check_x,)], getargs={'my_x':'t1.x'})
        my_runner = runner.Runner(depfile.name, reporter)

        # t2 gives chance for setup tasks to be executed
        assert False == my_runner.select_task(t2)
        assert ('start', t2) == reporter.log.pop(0)

        # execute task t1 to calculate value
        assert True == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        t1_result = my_runner.execute_task(t1)
        assert ('execute', t1) == reporter.log.pop(0)
        my_runner.process_task_result(t1, t1_result)
        assert ('success', t1) == reporter.log.pop(0)

        # t2.options are set on select_task
        assert {} == t2.options
        assert True == my_runner.select_task(t2)
        assert not reporter.log
        assert {'my_x': 1} == t2.options

    def test_getargs_fail(self, reporter, depfile):
        # invalid getargs. Exception wil be raised and task will fail
        def check_x(my_x): return True
        t1 = Task('t1', [lambda :True])
        t2 = Task('t2', [(check_x,)], getargs={'my_x':'t1.x'})
        my_runner = runner.Runner(depfile.name, reporter)

        # t2 gives chance for setup tasks to be executed
        assert False == my_runner.select_task(t2)
        assert ('start', t2) == reporter.log.pop(0)

        # execute task t1 to calculate value
        assert True == my_runner.select_task(t1)
        assert ('start', t1) == reporter.log.pop(0)
        t1_result = my_runner.execute_task(t1)
        assert ('execute', t1) == reporter.log.pop(0)
        my_runner.process_task_result(t1, t1_result)
        assert ('success', t1) == reporter.log.pop(0)

        # select_task t2 fails
        assert False == my_runner.select_task(t2)
        assert ('fail', t2) == reporter.log.pop(0)
        assert not reporter.log


class TestTask_Teardown(object):
    def test_ok(self, reporter, depfile):
        touched = []
        def touch():
            touched.append(1)
        t1 = Task('t1', [], teardown=[(touch,)])
        my_runner = runner.Runner(depfile.name, reporter)
        my_runner.teardown_list = [t1]
        my_runner.teardown()
        assert 1 == len(touched)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_reverse_order(self, reporter, depfile):
        def do_nothing():pass
        t1 = Task('t1', [], teardown=[do_nothing])
        t2 = Task('t2', [], teardown=[do_nothing])
        my_runner = runner.Runner(depfile.name, reporter)
        my_runner.teardown_list = [t1, t2]
        my_runner.teardown()
        assert ('teardown', t2) == reporter.log.pop(0)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_errors(self, reporter, depfile):
        def raise_something(x):
            raise Exception(x)
        t1 = Task('t1', [], teardown=[(raise_something,['t1 blow'])])
        t2 = Task('t2', [], teardown=[(raise_something,['t2 blow'])])
        my_runner = runner.Runner(depfile.name, reporter)
        my_runner.teardown_list = [t1, t2]
        my_runner.teardown()
        assert ('teardown', t2) == reporter.log.pop(0)
        assert ('cleanup_error',) == reporter.log.pop(0)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert ('cleanup_error',) == reporter.log.pop(0)
        assert not reporter.log


class TestTask_RunAll(object):
    def test_reporter_runtime_error(self, reporter, depfile):
        t1 = Task('t1', [], setup=['make_invalid'])
        my_runner = runner.Runner(depfile.name, reporter)
        tc = TaskControl([t1])
        tc.process(None)
        my_runner.run_all(tc)
        assert ('start', t1) == reporter.log.pop(0)
        assert ('runtime_error',) == reporter.log.pop(0)
        assert not reporter.log


# run tests in both single process runner and multi-process runner
def pytest_generate_tests(metafunc):
    if TestRunner_run_tasks == metafunc.cls:
        for RunnerClass in (runner.Runner, runner.MRunner):
            metafunc.addcall(id=RunnerClass.__name__,
                             funcargs=dict(RunnerClass=RunnerClass))



# decorator to force coverage on function.
# used to get coverage using multiprocessing.
def cov_dec(func): # pragma: no cover
    try:
        import coverage
    except:
        # coverage should not be required
        return func
    def wrap(*args, **kwargs):
        cov = coverage.coverage(data_suffix=True)
        cov.start()
        try:
            return  func(*args, **kwargs)
        finally:
            cov.stop()
            cov.save()
    return wrap


# monkey patch function executed in a subprocess to get coverage
# TODO - disabled because it was not working anymore...
#runner.MRunner.execute_task = cov_dec(runner.MRunner.execute_task)


def ok(): return "ok"
def ok2(): return "different"

class TestRunner_run_tasks(object):

    def test_teardown(self, reporter, RunnerClass, depfile):
        t1 = Task('t1', [], teardown=[ok])
        t2 = Task('t2', [])
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl([t1, t2])
        tc.process(None)
        assert [] == my_runner.teardown_list
        my_runner.run_tasks(tc)
        my_runner.finish()
        assert ('teardown', t1) == reporter.log[-1]

    # testing whole process/API
    def test_success(self, reporter, RunnerClass, depfile):
        tasks = [Task("taskX", [(my_print, ["out a"] )] ),
                 Task("taskY", [(my_print, ["out a"] )] )]
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0), reporter.log
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('success', tasks[0]) == reporter.log.pop(0)
        assert ('start', tasks[1]) == reporter.log.pop(0)
        assert ('execute', tasks[1]) == reporter.log.pop(0)
        assert ('success', tasks[1]) == reporter.log.pop(0)

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self, reporter, RunnerClass, depfile):
        tasks = [Task("taskX", [_fail]),
                 Task("taskY", [_fail])]
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
        assert runner.FAILURE == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    def test_error(self, reporter, RunnerClass, depfile):
        tasks = [Task("taskX", [_error]),
                 Task("taskY", [_error])]
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
        assert runner.ERROR == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('fail', tasks[0]) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    # when successful dependencies are updated
    def test_updateDependencies(self, reporter, RunnerClass, depfile):
        depPath = os.path.join(os.path.dirname(__file__),"data/dependency1")
        ff = open(depPath,"a")
        ff.write("xxx")
        ff.close()
        dependencies = [depPath]

        filePath = os.path.join(os.path.dirname(__file__),"data/target")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        tasks = [Task("taskX", [my_print], dependencies, targets)]
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
        assert runner.SUCCESS == my_runner.finish()
        d = Dependency(depfile.name)
        assert d._get("taskX", os.path.abspath(depPath))

    def test_resultDependency(self, reporter, RunnerClass, depfile):
        t1 = Task("t1", [(ok,)])
        t2 = Task("t2", [(ok,)], result_dep=['t1'])
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl([t1, t2])
        tc.process(None)
        my_runner.run_tasks(tc)
        my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)

        # again
        t1 = Task("t1", [(ok,)])
        t2 = Task("t2", [(ok,)], result_dep=['t1'])
        my_runner2 = RunnerClass(depfile.name, reporter)
        tc2 = TaskControl([t1, t2])
        tc2.process(None)
        my_runner2.run_tasks(tc2)
        my_runner2.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('up-to-date', t2) == reporter.log.pop(0)

        # change t1, t2 executed again
        t1B = Task("t1", [(ok2,)])
        t2 = Task("t2", [(ok,)], result_dep=['t1'])
        my_runner3 = RunnerClass(depfile.name, reporter)
        tc3 = TaskControl([t1B, t2])
        tc3.process(None)
        my_runner3.run_tasks(tc3)
        my_runner3.finish()
        assert ('start', t1B) == reporter.log.pop(0)
        assert ('execute', t1B) == reporter.log.pop(0)
        assert ('success', t1B) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)


    def test_continue(self, reporter, RunnerClass, depfile):
        tasks = [Task("task1", [(_fail,)] ),
                 Task("task2", [(_error,)] ),
                 Task("task3", [(ok,)])]
        my_runner = RunnerClass(depfile.name, reporter, continue_=True)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
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

    def test_getargs(self, reporter, RunnerClass, depfile):
        def use_args(arg1):
            print arg1
        def make_args(): return {'myarg':1}
        tasks = [Task("task1", [(use_args,)], getargs=dict(arg1="task2.myarg") ),
                 Task("task2", [(make_args,)])]
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl(tasks)
        tc.process(None)
        my_runner.run_tasks(tc)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', tasks[0]) == reporter.log.pop(0)
        assert ('start', tasks[1]) == reporter.log.pop(0)
        assert ('execute', tasks[1]) == reporter.log.pop(0)
        assert ('success', tasks[1]) == reporter.log.pop(0)
        assert ('execute', tasks[0]) == reporter.log.pop(0)
        assert ('success', tasks[0]) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    # SystemExit runner should not interfere with SystemExit
    def testSystemExitRaises(self, reporter, RunnerClass, depfile):
        t1 = Task("x", [_exit])
        my_runner = RunnerClass(depfile.name, reporter)
        tc = TaskControl([t1])
        tc.process(None)
        pytest.raises(SystemExit, my_runner.run_tasks, tc)
        my_runner.finish()


class TestMReporter(object):
    class MyRunner(object):
        def __init__(self):
            self.result_q = Queue()

    def testReporterMethod(self, reporter):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MRunner.MReporter(fake_runner, reporter)
        my_task = Task("task x", [])
        mp_reporter.add_success(my_task)
        got = fake_runner.result_q.get(True, 1)
        assert {'name': "task x", "reporter": 'add_success'} == got

    def testNonReporterMethod(self, reporter):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MRunner.MReporter(fake_runner, reporter)
        assert hasattr(mp_reporter, 'add_success')
        assert not hasattr(mp_reporter, 'no_existent_method')


class TestMRunner_get_next_task(object):
    # simple normal case
    def test_run_task(self, reporter, depfile):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        tc = TaskControl([t1, t2])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter)
        run._run_tasks_init(tc)
        assert t1 == run.get_next_task()
        assert t2 == run.get_next_task()
        assert None == run.get_next_task()

    def test_stop_running(self, reporter, depfile):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        tc = TaskControl([t1, t2])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter)
        run._run_tasks_init(tc)
        assert t1 == run.get_next_task()
        run._stop_running = True
        assert None == run.get_next_task()

    def test_waiting(self, reporter, depfile):
        t1 = Task('t1', [])
        t2a = Task('t2A', [], task_dep=('t1',))
        t2b = Task('t2B', [], setup=('t1',))
        t3 = Task('t3', [], setup=('t2B',))
        tc = TaskControl([t1, t2a, t2b, t3])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter)
        run._run_tasks_init(tc)

        # first task ok
        assert t1 == run.get_next_task()

        # hold until t1 finishes
        assert 0 == run.free_proc
        assert isinstance(run.get_next_task(), runner.Hold)
        assert {'t1':['t2A', 't2B'], 't2B': ['t3']} == run.waiting
        assert 1 == run.free_proc

        # ready for t2x
        assert [] == run.ready_queue
        run.process_task_result(t1, None)
        assert ['t2A', 't2B'] == run.ready_queue
        assert {'t2B': ['t3']} == run.waiting

        # t2
        assert t2a == run.get_next_task()
        assert t2b == run.get_next_task()

        # t3
        assert isinstance(run.get_next_task(), runner.Hold)
        run.process_task_result(t2b, None)
        assert ['t3'] == run.ready_queue
        assert {} == run.waiting
        assert t3 == run.get_next_task()
        assert None == run.get_next_task()


    def test_waiting_controller(self, reporter, depfile):
        t1 = Task('t1', [])
        t2a = Task('t2A', [], calc_dep=('t1',))
        tc = TaskControl([t1, t2a])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter)
        run._run_tasks_init(tc)

        # first task ok
        assert t1 == run.get_next_task()

        # hold until t1 finishes
        assert 0 == run.free_proc
        assert isinstance(run.get_next_task(), runner.Hold)
        assert 1 == run.free_proc


class TestMRunner_start_process(object):
    # 2 process, 3 tasks
    def test_all_processes(self, reporter, monkeypatch, depfile):
        mock_process = Mock()
        monkeypatch.setattr(runner, 'Process', mock_process)
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        tc = TaskControl([t1, t2])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter, num_process=2)
        run._run_tasks_init(tc)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 2 == len(proc_list)
        assert t1.name == task_q.get().name
        assert t2.name == task_q.get().name


    # 2 process, 1 task
    def test_less_processes(self, reporter, monkeypatch, depfile):
        mock_process = Mock()
        monkeypatch.setattr(runner, 'Process', mock_process)
        t1 = Task('t1', [])
        tc = TaskControl([t1])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter, num_process=2)
        run._run_tasks_init(tc)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 1 == len(proc_list)
        assert t1.name == task_q.get().name


    # 2 process, 2 tasks (but only one task can be started)
    def test_waiting_process(self, reporter, monkeypatch, depfile):
        mock_process = Mock()
        monkeypatch.setattr(runner, 'Process', mock_process)
        t1 = Task('t1', [])
        t2 = Task('t2', [], task_dep=['t1'])
        tc = TaskControl([t1, t2])
        tc.process(None)
        run = runner.MRunner(depfile.name, reporter, num_process=2)
        run._run_tasks_init(tc)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 2 == len(proc_list)
        assert t1.name == task_q.get().name
        assert isinstance(task_q.get(), runner.Hold)

class TestMRunner_execute_task(object):
    def test_hold(self, reporter, depfile):
        run = runner.MRunner(depfile.name, reporter)
        task_q = Queue()
        task_q.put(runner.Hold()) # to test
        task_q.put(None) # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q)
        run.finish()
        # nothing was done
        assert result_q.empty() # pragma: no cover (coverage bug?)

