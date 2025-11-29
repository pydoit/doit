import os
import sys
import platform

import pytest

from doit.exceptions import BaseFail, InvalidTask
from doit.dependency import DbmDB, Dependency
from doit.reporter import ConsoleReporter
from doit.task import Task, DelayedLoader
from doit.control import TaskControl
from doit import runner


PLAT_IMPL = platform.python_implementation()

# sample actions
def my_print(*args):
    pass
def _fail():
    return False
def _error():
    raise Exception("I am the exception.\n")
def _exit():
    raise SystemExit()
def simple_result():
    print("success output")
    print("success error", file=sys.stderr)
    return 'my-result'
def simple_fail():
    print("simple output")
    print("simple error", file=sys.stderr)
    raise Exception('this task failed')


def make_task_control(tasks, selected=None):
    """Helper to create TaskControl from task list.

    @param tasks: list of Task objects or dict {name: Task}
    @param selected: list of task names to select (None = all)
    """
    if isinstance(tasks, dict):
        task_list = list(tasks.values())
        if selected is None:
            selected = list(tasks.keys())
    else:
        task_list = tasks
        if selected is None:
            selected = [t.name for t in task_list]

    tc = TaskControl(task_list)
    tc.process(selected)
    return tc


class FakeReporter(object):
    """Just log everything in internal attribute - used on tests"""
    def __init__(self, with_exceptions=False, outstream=None, options=None):
        # include Exception object of log failures
        self.with_exceptions = with_exceptions
        self.log = []

    def get_status(self, task):
        self.log.append(('start', task))

    def execute_task(self, task):
        self.log.append(('execute', task))

    def add_failure(self, task, exception):
        if self.with_exceptions:
            self.log.append(('fail', task, exception))
        else:
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


@pytest.fixture
def reporter(request):
    return FakeReporter()


class TestRunner(object):
    def testInit(self, reporter, dep_manager):
        my_runner = runner.Runner(dep_manager, reporter)
        assert runner.ResultCode.SUCCESS == my_runner.final_result


class TestRunner_TaskExecution(object):
    """Test Runner behavior via run_all()."""

    def test_ready(self, reporter, dep_manager):
        """Task that should run gets executed."""
        t1 = Task("taskX", [(my_print, ["out a"])])
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.SUCCESS
        assert ('start', t1) == reporter.log[0]
        assert ('execute', t1) == reporter.log[1]
        assert ('success', t1) == reporter.log[2]

    def test_DependencyError(self, reporter, dep_manager):
        """Task with missing file_dep fails."""
        t1 = Task("taskX", [(my_print, ["out a"])],
                  file_dep=["i_dont_exist"])
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.ERROR
        assert ('start', t1) == reporter.log[0]
        assert ('fail', t1) == reporter.log[1]

    def test_upToDate(self, reporter, dep_manager):
        """Task that is up-to-date gets skipped."""
        t1 = Task("taskX", [(my_print, ["out a"])], file_dep=[__file__])
        dep_manager.save_success(t1)
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.SUCCESS
        assert ('start', t1) == reporter.log[0]
        assert ('up-to-date', t1) == reporter.log[1]

    def test_ignore(self, reporter, dep_manager):
        """Task that is ignored gets skipped."""
        t1 = Task("taskX", [(my_print, ["out a"])])
        dep_manager.ignore(t1)
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.SUCCESS
        assert ('start', t1) == reporter.log[0]
        assert ('ignore', t1) == reporter.log[1]

    def test_alwaysExecute(self, reporter, dep_manager):
        """Task runs even if up-to-date when always_execute=True."""
        t1 = Task("taskX", [(my_print, ["out a"])], uptodate=[True])
        dep_manager.save_success(t1)
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter, always_execute=True)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.SUCCESS
        assert ('start', t1) == reporter.log[0]
        assert ('execute', t1) == reporter.log[1]
        assert ('success', t1) == reporter.log[2]


class TestRunner_Getargs(object):
    """Test getargs behavior."""

    def test_getargs_ok(self, reporter, dep_manager):
        """getargs passes values from one task to another."""
        def ok(): return {'x': 1}
        def check_x(my_x): return my_x == 1
        t1 = Task('t1', [(ok,)])
        t2 = Task('t2', [(check_x,)], getargs={'my_x': ('t1', 'x')})
        tc = make_task_control({'t1': t1, 't2': t2}, ['t1', 't2'])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.SUCCESS
        assert {'my_x': 1} == t2.options

    def test_getargs_fail(self, reporter, dep_manager):
        """getargs fails when referenced key doesn't exist."""
        def check_x(my_x): return True
        t1 = Task('t1', [lambda: True])
        t2 = Task('t2', [(check_x,)], getargs={'my_x': ('t1', 'x')})
        tc = make_task_control({'t1': t1, 't2': t2}, ['t1', 't2'])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        # t2 should fail because t1 doesn't return 'x'
        assert result == runner.ResultCode.ERROR


class TestTask_Teardown(object):
    """Test teardown behavior via run_all()."""

    def test_ok(self, reporter, dep_manager):
        """Teardown runs after task execution."""
        touched = []
        def touch():
            touched.append(1)
        t1 = Task('t1', [lambda: True], teardown=[(touch,)])
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.run_all(tc)
        assert 1 == len(touched)
        # Find teardown in log
        teardown_logs = [l for l in reporter.log if l[0] == 'teardown']
        assert len(teardown_logs) == 1
        assert teardown_logs[0][1] == t1

    def test_reverse_order(self, reporter, dep_manager):
        """Teardowns run in reverse order of execution."""
        order = []
        def record1(): order.append('t1')
        def record2(): order.append('t2')
        t1 = Task('t1', [lambda: True], teardown=[(record1,)])
        t2 = Task('t2', [lambda: True], teardown=[(record2,)])
        tc = make_task_control([t1, t2])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.run_all(tc)
        # t2 teardown should run before t1 teardown
        assert order == ['t2', 't1']


class TestTask_RunAll(object):
    def test_reporter_runtime_error(self, reporter, dep_manager):
        """Runtime errors are reported."""
        t1 = Task('t1', [], calc_dep=['t2'])
        t2 = Task('t2', [lambda: {'file_dep': [1]}])
        tc = make_task_control({'t1': t1, 't2': t2}, ['t1', 't2'])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.ERROR
        assert ('runtime_error',) in reporter.log


# run tests in both single process runner and multi-thread runner
RUNNERS = [runner.Runner, runner.MThreadRunner]


@pytest.fixture(params=RUNNERS)
def RunnerClass(request):
    return request.param


# function used on actions, define here to make sure they are pickable
def ok(): return "ok"
def ok2(): return "different"
def my_action():
    import sys
    sys.stdout.write('out here')
    sys.stderr.write('err here')
    return {'bb': 5}
def use_args(arg1):
    print(arg1)
def make_args():
    return {'myarg': 1}
def action_add_filedep(task, extra_dep):
    task.file_dep.add(extra_dep)


class TestRunner_run_all(object):

    def test_teardown(self, reporter, RunnerClass, dep_manager):
        """Teardown runs after task completes."""
        t1 = Task('t1', [lambda: True], teardown=[ok])
        t2 = Task('t2', [lambda: True])
        tc = make_task_control([t1, t2])
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_all(tc)
        # Check teardown was called
        teardown_logs = [l for l in reporter.log if l[0] == 'teardown']
        assert len(teardown_logs) == 1
        assert teardown_logs[0][1] == t1

    # testing whole process/API
    def test_success(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(my_print, ["out a"])])
        t2 = Task("t2", [(my_print, ["out a"])])
        tc = make_task_control([t1, t2])
        my_runner = RunnerClass(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        # Check that both tasks were started, executed, and succeeded
        # Order may vary for parallel runners
        log_types = [l[0] for l in reporter.log]
        log_tasks = [l[1] for l in reporter.log]
        assert log_types.count('start') == 2
        assert log_types.count('execute') == 2
        assert log_types.count('success') == 2
        assert t1 in log_tasks
        assert t2 in log_tasks

    # test result, value, out, err are saved into task
    def test_result(self, reporter, RunnerClass, dep_manager):
        task = Task("taskY", [my_action])
        tc = make_task_control([task])
        my_runner = RunnerClass(dep_manager, reporter)
        assert None == task.result
        assert {} == task.values
        assert [None] == [a.out for a in task.actions]
        assert [None] == [a.err for a in task.actions]
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        assert {'bb': 5} == task.result
        assert {'bb': 5} == task.values
        assert ['out here'] == [a.out for a in task.actions]
        assert ['err here'] == [a.err for a in task.actions]

    # whenever a task fails remaining task are not executed (sequential runner)
    def test_failureOutput_sequential(self, reporter, dep_manager):
        """Sequential runner stops after first failure."""
        t1 = Task("t1", [_fail])
        t2 = Task("t2", [_fail])
        tc = make_task_control([t1, t2])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.FAILURE == result
        # Only t1 should be executed
        execute_logs = [l for l in reporter.log if l[0] == 'execute']
        assert len(execute_logs) == 1
        assert execute_logs[0][1] == t1

    def test_failureOutput_parallel(self, reporter, dep_manager):
        """Parallel runner may execute tasks before failure is detected."""
        t1 = Task("t1", [_fail])
        t2 = Task("t2", [_fail])
        tc = make_task_control([t1, t2])
        my_runner = runner.MThreadRunner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        # Both tasks may have been executed (they're independent)
        assert result in (runner.ResultCode.FAILURE, runner.ResultCode.ERROR)
        fail_logs = [l for l in reporter.log if l[0] == 'fail']
        assert len(fail_logs) >= 1  # At least one failure

    def test_error_sequential(self, reporter, dep_manager):
        """Sequential runner stops after first error."""
        t1 = Task("t1", [_error])
        t2 = Task("t2", [_error])
        tc = make_task_control([t1, t2])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.ERROR == result
        # Only t1 should be executed
        execute_logs = [l for l in reporter.log if l[0] == 'execute']
        assert len(execute_logs) == 1
        assert execute_logs[0][1] == t1

    def test_error_parallel(self, reporter, dep_manager):
        """Parallel runner may execute tasks before error is detected."""
        t1 = Task("t1", [_error])
        t2 = Task("t2", [_error])
        tc = make_task_control([t1, t2])
        my_runner = runner.MThreadRunner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert result == runner.ResultCode.ERROR
        fail_logs = [l for l in reporter.log if l[0] == 'fail']
        assert len(fail_logs) >= 1

    def test_dependency_error_after_execution(self, dep_manager):
        t1 = Task("t1", [(my_print, ["out a"])],
                  file_dep=["i_dont_exist"], targets=['not_there'])
        reporter = FakeReporter(with_exceptions=True)
        tc = make_task_control([t1])
        my_runner = runner.Runner(dep_manager, reporter)
        # Missing file_dep is not caught because check is short-circuited by
        # missing target.
        result = my_runner.run_all(tc)
        assert runner.ResultCode.ERROR == result
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        fail_log = reporter.log.pop(0)
        assert ('fail', t1) == fail_log[:2]
        assert "Dependent file 'i_dont_exist' does not exist" in str(fail_log[2])

    # when successful dependencies are updated
    def test_updateDependencies(self, reporter, RunnerClass, depfile_name):
        depPath = os.path.join(os.path.dirname(__file__), "data", "dependency1")
        ff = open(depPath, "a")
        ff.write("xxx")
        ff.close()
        dependencies = [depPath]

        filePath = os.path.join(os.path.dirname(__file__), "data", "target")
        ff = open(filePath, "a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        t1 = Task("t1", [my_print], dependencies, targets)
        tc = make_task_control([t1])
        dep_manager = Dependency(DbmDB, depfile_name)
        my_runner = RunnerClass(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        d = Dependency(DbmDB, depfile_name)
        assert d._get("t1", os.path.abspath(depPath))

    def test_continue(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(_fail,)])
        t2 = Task("t2", [(_error,)])
        t3 = Task("t3", [(ok,)])
        tc = make_task_control([t1, t2, t3])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.ERROR == result
        # In continue mode, all 3 tasks should be executed
        execute_logs = [l for l in reporter.log if l[0] == 'execute']
        assert len(execute_logs) == 3
        # t1 and t2 should fail, t3 should succeed
        fail_logs = [l for l in reporter.log if l[0] == 'fail']
        assert len(fail_logs) == 2
        fail_tasks = [l[1] for l in fail_logs]
        assert t1 in fail_tasks
        assert t2 in fail_tasks
        success_logs = [l for l in reporter.log if l[0] == 'success']
        assert len(success_logs) == 1
        assert success_logs[0][1] == t3

    def test_continue_dont_execute_parent_of_failed_task(self, reporter,
                                                         RunnerClass, dep_manager):
        t1 = Task("t1", [(_error,)])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        t3 = Task("t3", [(ok,)])
        tc = make_task_control([t1, t2, t3])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.ERROR == result
        # t1 and t3 should be executed, but not t2 (depends on failed t1)
        execute_logs = [l for l in reporter.log if l[0] == 'execute']
        execute_tasks = [l[1] for l in execute_logs]
        assert t1 in execute_tasks
        assert t3 in execute_tasks
        # t2 should not be executed (but may be started/checked)
        assert t2 not in execute_tasks
        # t1 should fail
        fail_logs = [l for l in reporter.log if l[0] == 'fail']
        fail_tasks = [l[1] for l in fail_logs]
        assert t1 in fail_tasks

    def test_continue_dep_error(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(ok,)], file_dep=['i_dont_exist'])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        tc = make_task_control([t1, t2])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.ERROR == result
        # t1 should fail due to missing file_dep
        fail_logs = [l for l in reporter.log if l[0] == 'fail']
        assert len(fail_logs) >= 1
        fail_tasks = [l[1] for l in fail_logs]
        assert t1 in fail_tasks

    def test_continue_ignored_dep(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(ok,)])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        dep_manager.ignore(t1)
        tc = make_task_control([t1, t2])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        assert ('start', t1) == reporter.log.pop(0)
        assert ('ignore', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('ignore', t2) == reporter.log.pop(0)
        assert 0 == len(reporter.log)

    def test_getargs_sequential(self, reporter, dep_manager):
        """Test getargs with sequential runner (setup tasks handled correctly)."""
        t1 = Task("t1", [(use_args,)], getargs=dict(arg1=('t2', 'myarg')))
        t2 = Task("t2", [(make_args,)])
        tc = make_task_control({'t1': t1, 't2': t2}, ['t1', 't2'])
        my_runner = runner.Runner(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        # Both tasks should succeed
        success_logs = [l for l in reporter.log if l[0] == 'success']
        assert len(success_logs) == 2
        # t2 must be executed before t1 (getargs dependency)
        execute_logs = [l for l in reporter.log if l[0] == 'execute']
        t2_idx = next(i for i, l in enumerate(execute_logs) if l[1] == t2)
        t1_idx = next(i for i, l in enumerate(execute_logs) if l[1] == t1)
        assert t2_idx < t1_idx, "t2 must execute before t1 (getargs dependency)"

    def testActionModifiesFiledep(self, reporter, RunnerClass, dep_manager):
        extra_dep = os.path.join(os.path.dirname(__file__), 'sample_md5.txt')
        t1 = Task("t1", [(my_print, ["out a"]),
                         (action_add_filedep, (), {'extra_dep': extra_dep})
                         ])
        tc = make_task_control([t1])
        my_runner = RunnerClass(dep_manager, reporter)
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        assert ('start', t1) == reporter.log.pop(0), reporter.log
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert t1.file_dep == set([extra_dep])

    # SystemExit runner should not interfere with SystemExit
    def testSystemExitRaises(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [_exit])
        tc = make_task_control([t1])
        my_runner = RunnerClass(dep_manager, reporter)
        pytest.raises(SystemExit, my_runner.run_all, tc)


def non_pickable_creator():
    return {'basename': 't2', 'actions': [lambda: True]}


class TestMThreadRunner_run_all(object):

    def test_task_not_picklable_thread(self, reporter, dep_manager):
        """Threaded runner handles non-picklable tasks."""
        t1 = Task("t1", [(my_print, ["out a"])])
        t2 = Task("t2", None, loader=DelayedLoader(
            non_pickable_creator, executed='t1'))
        tc = make_task_control({'t1': t1, 't2': t2}, ['t1', 't2'])
        my_runner = runner.MThreadRunner(dep_manager, reporter)
        # threaded code have no problems with closures
        result = my_runner.run_all(tc)
        assert runner.ResultCode.SUCCESS == result
        assert ('start', t1) == reporter.log.pop(0), reporter.log
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)


def test_MThreadRunner_available():
    assert runner.MThreadRunner.available() == True
