import os
import sys
import pickle
import unittest
from multiprocessing import Queue
import platform
from unittest.mock import Mock, patch

from doit.exceptions import BaseFail, InvalidTask
from doit.dependency import DbmDB, Dependency
from doit.reporter import ConsoleReporter
from doit.task import Task, DelayedLoader
from doit.control import TaskDispatcher, ExecNode
from doit import runner

from tests.support import DepManagerMixin, DepfileNameMixin


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


class TestRunner(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def testInit(self):
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        self.assertFalse(my_runner._stop_running)
        self.assertEqual(runner.SUCCESS, my_runner.final_result)


class TestRunner_SelectTask(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def test_ready(self):
        t1 = Task("taskX", [(my_print, ["out a"])])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        self.assertTrue(my_runner.select_task(ExecNode(t1, None), {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_DependencyError(self):
        t1 = Task("taskX", [(my_print, ["out a"])],
                  file_dep=["i_dont_exist"])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        self.assertFalse(my_runner.select_task(ExecNode(t1, None), {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_upToDate(self):
        t1 = Task("taskX", [(my_print, ["out a"])], file_dep=[__file__])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.dep_manager.save_success(t1)
        self.assertFalse(my_runner.select_task(ExecNode(t1, None), {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('up-to-date', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_ignore(self):
        t1 = Task("taskX", [(my_print, ["out a"])])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.dep_manager.ignore(t1)
        self.assertFalse(my_runner.select_task(ExecNode(t1, None), {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('ignore', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_alwaysExecute(self):
        t1 = Task("taskX", [(my_print, ["out a"])], uptodate=[True])
        my_runner = runner.Runner(self.dep_manager, self.reporter,
                                  always_execute=True)
        my_runner.dep_manager.save_success(t1)
        n1 = ExecNode(t1, None)
        self.assertTrue(my_runner.select_task(n1, {}))
        # run_status is set to run even if task is up-to-date
        self.assertEqual(n1.run_status, 'run')
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_noSetup_ok(self):
        t1 = Task("taskX", [(my_print, ["out a"])])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        self.assertTrue(my_runner.select_task(ExecNode(t1, None), {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_withSetup(self):
        t1 = Task("taskX", [(my_print, ["out a"])], setup=["taskY"])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        # defer execution
        n1 = ExecNode(t1, None)
        self.assertFalse(my_runner.select_task(n1, {}))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)
        # trying to select again
        self.assertTrue(my_runner.select_task(n1, {}))
        self.assertFalse(self.reporter.log)

    def test_getargs_ok(self):
        def ok(): return {'x': 1}
        def check_x(my_x): return my_x == 1
        t1 = Task('t1', [(ok,)])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', [(check_x,)], getargs={'my_x': ('t1', 'x')})
        n2 = ExecNode(t2, None)
        tasks_dict = {'t1': t1, 't2': t2}
        my_runner = runner.Runner(self.dep_manager, self.reporter)

        # t2 gives chance for setup tasks to be executed
        self.assertFalse(my_runner.select_task(n2, tasks_dict))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))

        # execute task t1 to calculate value
        self.assertTrue(my_runner.select_task(n1, tasks_dict))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        t1_result = my_runner.execute_task(t1)
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        my_runner.process_task_result(n1, t1_result)
        self.assertEqual(('success', t1), self.reporter.log.pop(0))

        # t2.options are set on select_task
        self.assertTrue(my_runner.select_task(n2, tasks_dict))
        self.assertFalse(self.reporter.log)
        self.assertEqual({'my_x': 1}, t2.options)

    def test_getargs_fail(self):
        # invalid getargs. Exception will be raised and task will fail
        def check_x(my_x): return True
        t1 = Task('t1', [lambda: True])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', [(check_x,)], getargs={'my_x': ('t1', 'x')})
        n2 = ExecNode(t2, None)
        tasks_dict = {'t1': t1, 't2': t2}
        my_runner = runner.Runner(self.dep_manager, self.reporter)

        # t2 gives chance for setup tasks to be executed
        self.assertFalse(my_runner.select_task(n2, tasks_dict))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))

        # execute task t1 to calculate value
        self.assertTrue(my_runner.select_task(n1, tasks_dict))
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        t1_result = my_runner.execute_task(t1)
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        my_runner.process_task_result(n1, t1_result)
        self.assertEqual(('success', t1), self.reporter.log.pop(0))

        # select_task t2 fails
        self.assertFalse(my_runner.select_task(n2, tasks_dict))
        self.assertEqual(('fail', t2), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_getargs_dict(self):
        def ok(): return {'x': 1}
        t1 = Task('t1', [(ok,)])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', None, getargs={'my_x': ('t1', None)})
        tasks_dict = {'t1': t1, 't2': t2}
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        t1_result = my_runner.execute_task(t1)
        my_runner.process_task_result(n1, t1_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        self.assertEqual({'my_x': {'x': 1}}, t2.options)

    def test_getargs_group(self):
        def ok(): return {'x': 1}
        t1 = Task('t1', None, task_dep=['t1:a'], has_subtask=True)
        t1a = Task('t1:a', [(ok,)], subtask_of='t1')
        t2 = Task('t2', None, getargs={'my_x': ('t1', None)})
        tasks_dict = {'t1': t1, 't1a': t1a, 't2': t2}
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        t1a_result = my_runner.execute_task(t1a)
        my_runner.process_task_result(ExecNode(t1a, None), t1a_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        self.assertEqual({'my_x': {'a': {'x': 1}}}, t2.options)

    def test_getargs_group_value(self):
        def ok(): return {'x': 1}
        t1 = Task('t1', None, task_dep=['t1:a'], has_subtask=True)
        t1a = Task('t1:a', [(ok,)], subtask_of='t1')
        t2 = Task('t2', None, getargs={'my_x': ('t1', 'x')})
        tasks_dict = {'t1': t1, 't1a': t1a, 't2': t2}
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        t1a_result = my_runner.execute_task(t1a)
        my_runner.process_task_result(ExecNode(t1a, None), t1a_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        self.assertEqual({'my_x': {'a': 1}}, t2.options)


class TestTask_Teardown(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def test_ok(self):
        touched = []
        def touch():
            touched.append(1)
        t1 = Task('t1', [], teardown=[(touch,)])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.teardown_list = [t1]
        t1.execute(my_runner.stream)
        my_runner.teardown()
        self.assertEqual(1, len(touched))
        self.assertEqual(('teardown', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_reverse_order(self):
        def do_nothing(): pass
        t1 = Task('t1', [], teardown=[do_nothing])
        t2 = Task('t2', [], teardown=[do_nothing])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.teardown_list = [t1, t2]
        t1.execute(my_runner.stream)
        t2.execute(my_runner.stream)
        my_runner.teardown()
        self.assertEqual(('teardown', t2), self.reporter.log.pop(0))
        self.assertEqual(('teardown', t1), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)

    def test_errors(self):
        def raise_something(x):
            raise Exception(x)
        t1 = Task('t1', [], teardown=[(raise_something, ['t1 blow'])])
        t2 = Task('t2', [], teardown=[(raise_something, ['t2 blow'])])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.teardown_list = [t1, t2]
        t1.execute(my_runner.stream)
        t2.execute(my_runner.stream)
        my_runner.teardown()
        self.assertEqual(('teardown', t2), self.reporter.log.pop(0))
        self.assertEqual(('cleanup_error',), self.reporter.log.pop(0))
        self.assertEqual(('teardown', t1), self.reporter.log.pop(0))
        self.assertEqual(('cleanup_error',), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)


class TestTask_RunAll(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def test_reporter_runtime_error(self):
        t1 = Task('t1', [], calc_dep=['t2'])
        t2 = Task('t2', [lambda: {'file_dep': [1]}])
        my_runner = runner.Runner(self.dep_manager, self.reporter)
        my_runner.run_all(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                         ['t1', 't2']))
        self.assertEqual(runner.ERROR, my_runner.final_result)
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t2), self.reporter.log.pop(0))
        self.assertEqual(('success', t2), self.reporter.log.pop(0))
        self.assertEqual(('runtime_error',), self.reporter.log.pop(0))
        self.assertFalse(self.reporter.log)


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


# ---------------------------------------------------------------------------
# TestRunner_run_tasks: parametrized over Runner, MThreadRunner, MRunner
# ---------------------------------------------------------------------------

class RunnerRunTasksBase:
    """Mixin with tests -- not discovered by rut because it does not
    inherit unittest.TestCase directly."""
    runner_class = None

    def test_teardown(self):
        t1 = Task('t1', [], teardown=[ok])
        t2 = Task('t2', [])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        self.assertEqual([], my_runner.teardown_list)
        my_runner.run_tasks(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        my_runner.finish()
        self.assertEqual(('teardown', t1), self.reporter.log[-1])

    # testing whole process/API
    def test_success(self):
        t1 = Task("t1", [(my_print, ["out a"])])
        t2 = Task("t2", [(my_print, ["out a"])])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('success', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t2), self.reporter.log.pop(0))
        self.assertEqual(('success', t2), self.reporter.log.pop(0))

    # test result, value, out, err are saved into task
    def test_result(self):
        task = Task("taskY", [my_action])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        self.assertIsNone(task.result)
        self.assertEqual({}, task.values)
        self.assertEqual([None], [a.out for a in task.actions])
        self.assertEqual([None], [a.err for a in task.actions])
        my_runner.run_tasks(TaskDispatcher({'taskY': task}, [], ['taskY']))
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual({'bb': 5}, task.result)
        self.assertEqual({'bb': 5}, task.values)
        self.assertEqual(['out here'], [a.out for a in task.actions])
        self.assertEqual(['err here'], [a.err for a in task.actions])

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self):
        t1 = Task("t1", [_fail])
        t2 = Task("t2", [_fail])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(runner.FAILURE, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        # second task is not executed
        self.assertEqual(0, len(self.reporter.log))

    def test_error(self):
        t1 = Task("t1", [_error])
        t2 = Task("t2", [_error])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(runner.ERROR, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        # second task is not executed
        self.assertEqual(0, len(self.reporter.log))

    # when successful dependencies are updated
    def test_updateDependencies(self):
        tests_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "tests"))
        depPath = os.path.join(tests_dir, "data", "dependency1")
        ff = open(depPath, "a")
        ff.write("xxx")
        ff.close()
        dependencies = [depPath]

        filePath = os.path.join(tests_dir, "data", "target")
        ff = open(filePath, "a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        t1 = Task("t1", [my_print], dependencies, targets)
        dep_manager = Dependency(DbmDB, self.depfile_name)
        my_runner = self.runner_class(dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1}, [], ['t1']))
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        d = Dependency(DbmDB, self.depfile_name)
        self.assertTrue(d._get("t1", os.path.abspath(depPath)))

    def test_continue(self):
        t1 = Task("t1", [(_fail,)])
        t2 = Task("t2", [(_error,)])
        t3 = Task("t3", [(ok,)])
        my_runner = self.runner_class(self.dep_manager, self.reporter,
                                      continue_=True)
        disp = TaskDispatcher({'t1': t1, 't2': t2, 't3': t3}, [],
                              ['t1', 't2', 't3'])
        my_runner.run_tasks(disp)
        self.assertEqual(runner.ERROR, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t2), self.reporter.log.pop(0))
        self.assertEqual(('fail', t2), self.reporter.log.pop(0))
        self.assertEqual(('start', t3), self.reporter.log.pop(0))
        self.assertEqual(('execute', t3), self.reporter.log.pop(0))
        self.assertEqual(('success', t3), self.reporter.log.pop(0))
        self.assertEqual(0, len(self.reporter.log))

    def test_continue_dont_execute_parent_of_failed_task(self):
        t1 = Task("t1", [(_error,)])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        t3 = Task("t3", [(ok,)])
        my_runner = self.runner_class(self.dep_manager, self.reporter,
                                      continue_=True)
        disp = TaskDispatcher({'t1': t1, 't2': t2, 't3': t3}, [],
                              ['t1', 't2', 't3'])
        my_runner.run_tasks(disp)
        self.assertEqual(runner.ERROR, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('fail', t2), self.reporter.log.pop(0))
        self.assertEqual(('start', t3), self.reporter.log.pop(0))
        self.assertEqual(('execute', t3), self.reporter.log.pop(0))
        self.assertEqual(('success', t3), self.reporter.log.pop(0))
        self.assertEqual(0, len(self.reporter.log))

    def test_continue_dep_error(self):
        t1 = Task("t1", [(ok,)], file_dep=['i_dont_exist'])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        my_runner = self.runner_class(self.dep_manager, self.reporter,
                                      continue_=True)
        disp = TaskDispatcher({'t1': t1, 't2': t2}, [], ['t1', 't2'])
        my_runner.run_tasks(disp)
        self.assertEqual(runner.ERROR, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('fail', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('fail', t2), self.reporter.log.pop(0))
        self.assertEqual(0, len(self.reporter.log))

    def test_continue_ignored_dep(self):
        t1 = Task("t1", [(ok,)])
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        my_runner = self.runner_class(self.dep_manager, self.reporter,
                                      continue_=True)
        my_runner.dep_manager.ignore(t1)
        disp = TaskDispatcher({'t1': t1, 't2': t2}, [], ['t1', 't2'])
        my_runner.run_tasks(disp)
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('ignore', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('ignore', t2), self.reporter.log.pop(0))
        self.assertEqual(0, len(self.reporter.log))

    def test_getargs(self):
        t1 = Task("t1", [(use_args,)],
                  getargs=dict(arg1=('t2', 'myarg')))
        t2 = Task("t2", [(make_args,)])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t2), self.reporter.log.pop(0))
        self.assertEqual(('success', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('success', t1), self.reporter.log.pop(0))
        self.assertEqual(0, len(self.reporter.log))

    def testActionModifiesFiledep(self):
        extra_dep = os.path.join(os.path.dirname(__file__), '..',
                                 'tests', 'sample_md5.txt')
        t1 = Task("t1", [(my_print, ["out a"]),
                         (action_add_filedep, (),
                          {'extra_dep': extra_dep})])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        my_runner.run_tasks(TaskDispatcher({'t1': t1}, [], ['t1']))
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('success', t1), self.reporter.log.pop(0))
        self.assertEqual(t1.file_dep, set([extra_dep]))

    # SystemExit runner should not interfere with SystemExit
    def testSystemExitRaises(self):
        t1 = Task("t1", [_exit])
        my_runner = self.runner_class(self.dep_manager, self.reporter)
        disp = TaskDispatcher({'t1': t1}, [], ['t1'])
        self.assertRaises(SystemExit, my_runner.run_tasks, disp)
        my_runner.finish()


class TestRunnerRunTasks_Runner(RunnerRunTasksBase, DepManagerMixin,
                                DepfileNameMixin, unittest.TestCase):
    runner_class = runner.Runner

    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def test_dependency_error_after_execution(self):
        t1 = Task("t1", [(my_print, ["out a"])],
                  file_dep=["i_dont_exist"], targets=['not_there'])
        reporter = FakeReporter(with_exceptions=True)
        my_runner = runner.Runner(self.dep_manager, reporter)
        # Missing file_dep is not caught because check is short-circuited
        # by missing target.
        my_runner.run_tasks(TaskDispatcher({'t1': t1}, [], ['t1']))
        self.assertEqual(runner.ERROR, my_runner.finish())
        self.assertEqual(('start', t1), reporter.log.pop(0))
        self.assertEqual(('execute', t1), reporter.log.pop(0))
        fail_log = reporter.log.pop(0)
        self.assertEqual(('fail', t1), fail_log[:2])
        self.assertIn("Dependent file 'i_dont_exist' does not exist",
                       str(fail_log[2]))
        self.assertFalse(reporter.log)


class TestRunnerRunTasks_MThread(RunnerRunTasksBase, DepManagerMixin,
                                 DepfileNameMixin, unittest.TestCase):
    runner_class = runner.MThreadRunner

    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()


@unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
class TestRunnerRunTasks_MRunner(RunnerRunTasksBase, DepManagerMixin,
                                 DepfileNameMixin, unittest.TestCase):
    runner_class = runner.MRunner

    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()


# ---------------------------------------------------------------------------
# TestMReporter
# ---------------------------------------------------------------------------

@unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
class TestMReporter(unittest.TestCase):
    class MyRunner(object):
        def __init__(self):
            self.result_q = Queue()

    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def testReporterMethod(self):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MReporter(fake_runner, self.reporter)
        my_task = Task("task x", [])
        mp_reporter.add_success(my_task)
        # note limit is 2 seconds because of
        # http://bugs.python.org/issue17707
        got = fake_runner.result_q.get(True, 2)
        self.assertEqual({'name': "task x", "reporter": 'add_success'}, got)

    def testNonReporterMethod(self):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MReporter(fake_runner, self.reporter)
        self.assertTrue(hasattr(mp_reporter, 'add_success'))
        self.assertFalse(hasattr(mp_reporter, 'no_existent_method'))


# ---------------------------------------------------------------------------
# cloudpickle helper
# ---------------------------------------------------------------------------

def cloudpickle_installed():
    try:
        import cloudpickle
        cloudpickle
    except ImportError:
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# TestJobTask
# ---------------------------------------------------------------------------

class TestJobTask(unittest.TestCase):
    @unittest.skipIf(not cloudpickle_installed(),
                     'cloudpickle not installed')
    def test_closure_is_picklable(self):
        # can pickle because we use cloudpickle
        def non_top_function(): return 4
        t1 = Task('t1', [non_top_function])
        t1p = runner.JobTask(t1).task_pickle
        t2 = pickle.loads(t1p)
        self.assertEqual(4, t2.actions[0].py_callable())

    def test_not_picklable_raises_InvalidTask(self):
        def non_top_function(): pass
        class Unpicklable:
            def __getstate__(self):
                raise pickle.PicklingError("DO NOT PICKLE")
        d1 = Unpicklable()
        t1 = Task('t1', [non_top_function, (d1,)])
        self.assertRaises(InvalidTask, runner.JobTask, t1)


# ---------------------------------------------------------------------------
# test_MRunner_pickable (was bare function)
# ---------------------------------------------------------------------------

class TestMRunnerPickable(DepManagerMixin, unittest.TestCase):
    # multiprocessing on Windows requires the whole object to be pickable
    def test_MRunner_pickable(self):
        t1 = Task('t1', [])
        reporter = ConsoleReporter(sys.stdout, {})
        run = runner.MRunner(self.dep_manager, reporter)
        run._run_tasks_init(TaskDispatcher({'t1': t1}, [], ['t1']))
        # assert nothing is raised
        pickle.dumps(run)


# ---------------------------------------------------------------------------
# TestMRunner_get_next_job
# ---------------------------------------------------------------------------

@unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
class TestMRunner_get_next_job(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    # simple normal case
    def test_run_task(self):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        run = runner.MRunner(self.dep_manager, self.reporter)
        run._run_tasks_init(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(t1.name, run.get_next_job(None).name)
        self.assertEqual(t2.name, run.get_next_job(None).name)
        self.assertIsNone(run.get_next_job(None))

    def test_stop_running(self):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        run = runner.MRunner(self.dep_manager, self.reporter)
        run._run_tasks_init(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))
        self.assertEqual(t1.name, run.get_next_job(None).name)
        run._stop_running = True
        self.assertIsNone(run.get_next_job(None))

    def test_waiting(self):
        t1 = Task('t1', [])
        t2 = Task('t2', [], setup=('t1',))
        run = runner.MRunner(self.dep_manager, self.reporter)
        dispatcher = TaskDispatcher({'t1': t1, 't2': t2}, [], ['t2'])
        run._run_tasks_init(dispatcher)

        # first start task 1
        j1 = run.get_next_job(None)
        self.assertEqual(t1.name, j1.name)

        # hold until t1 is done
        self.assertIsInstance(run.get_next_job(None), runner.JobHold)
        self.assertIsInstance(run.get_next_job(None), runner.JobHold)

        n1 = dispatcher.nodes[j1.name]
        n1.run_status = 'done'
        j2 = run.get_next_job(n1)
        self.assertEqual(t2.name, j2.name)
        self.assertIsNone(run.get_next_job(dispatcher.nodes[j2.name]))

    def test_waiting_controller(self):
        t1 = Task('t1', [])
        t2 = Task('t2', [], calc_dep=('t1',))
        run = runner.MRunner(self.dep_manager, self.reporter)
        run._run_tasks_init(TaskDispatcher({'t1': t1, 't2': t2}, [],
                                           ['t1', 't2']))

        # first task ok
        self.assertEqual(t1.name, run.get_next_job(None).name)

        # hold until t1 finishes
        self.assertEqual(0, run.free_proc)
        self.assertIsInstance(run.get_next_job(None), runner.JobHold)
        self.assertEqual(1, run.free_proc)

    def test_delayed_loaded(self):
        def create():
            return {'basename': 't1', 'actions': None}
        t1 = Task('t1', [], loader=DelayedLoader(create, executed='t2'))
        t2 = Task('t2', [])
        run = runner.MRunner(self.dep_manager, self.reporter)
        dispatcher = TaskDispatcher({'t1': t1, 't2': t2}, [],
                                     ['t1', 't2'])
        run._run_tasks_init(dispatcher)
        self.assertEqual(t2.name, run.get_next_job(None).name)
        self.assertEqual(runner.JobHold.type,
                         run.get_next_job(None).type)

        # after t2 is done t1 can be dispatched
        n2 = dispatcher.nodes[t2.name]
        n2.run_status = 'done'
        j1 = run.get_next_job(n2)
        self.assertEqual(t1.name, j1.name)
        # the job for t1 contains the whole task since sub-process dont
        # have it
        self.assertEqual(j1.type, runner.JobTask.type)


# ---------------------------------------------------------------------------
# TestMRunner_start_process
# ---------------------------------------------------------------------------

@unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
class TestMRunner_start_process(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    # 2 process, 3 tasks
    def test_all_processes(self):
        with patch.object(runner.MRunner, 'Child', Mock()):
            t1 = Task('t1', [])
            t2 = Task('t2', [])
            td = TaskDispatcher({'t1': t1, 't2': t2}, [], ['t1', 't2'])
            run = runner.MRunner(self.dep_manager, self.reporter,
                                 num_process=2)
            run._run_tasks_init(td)
            result_q = Queue()
            task_q = Queue()

            proc_list = run._run_start_processes(task_q, result_q)
            run.finish()
            self.assertEqual(2, len(proc_list))
            self.assertEqual(t1.name, task_q.get().name)
            self.assertEqual(t2.name, task_q.get().name)

    # 2 process, 1 task
    def test_less_processes(self):
        with patch.object(runner.MRunner, 'Child', Mock()):
            t1 = Task('t1', [])
            td = TaskDispatcher({'t1': t1}, [], ['t1'])
            run = runner.MRunner(self.dep_manager, self.reporter,
                                 num_process=2)
            run._run_tasks_init(td)
            result_q = Queue()
            task_q = Queue()

            proc_list = run._run_start_processes(task_q, result_q)
            run.finish()
            self.assertEqual(1, len(proc_list))
            self.assertEqual(t1.name, task_q.get().name)

    # 2 process, 2 tasks (but only one task can be started)
    def test_waiting_process(self):
        with patch.object(runner.MRunner, 'Child', Mock()):
            t1 = Task('t1', [])
            t2 = Task('t2', [], task_dep=['t1'])
            td = TaskDispatcher({'t1': t1, 't2': t2}, [],
                                 ['t1', 't2'])
            run = runner.MRunner(self.dep_manager, self.reporter,
                                 num_process=2)
            run._run_tasks_init(td)
            result_q = Queue()
            task_q = Queue()

            proc_list = run._run_start_processes(task_q, result_q)
            run.finish()
            self.assertEqual(2, len(proc_list))
            self.assertEqual(t1.name, task_q.get().name)
            self.assertIsInstance(task_q.get(), runner.JobHold)


# ---------------------------------------------------------------------------
# TestMRunner_parallel_run_tasks
# ---------------------------------------------------------------------------

def non_pickable_creator():
    return {'basename': 't2', 'actions': [lambda: True]}


class TestMRunner_parallel_run_tasks(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    @unittest.skipIf(not runner.MRunner.available(),
                     'MRunner not available')
    @unittest.skipIf(not cloudpickle_installed(),
                     'cloudpickle not installed')
    def test_task_cloudpicklabe_multiprocess(self):
        t1 = Task("t1", [(my_print, ["out a"])])
        t2 = Task("t2", None, loader=DelayedLoader(
            non_pickable_creator, executed='t1'))
        my_runner = runner.MRunner(self.dep_manager, self.reporter)
        dispatcher = TaskDispatcher({'t1': t1, 't2': t2}, [],
                                     ['t1', 't2'])
        my_runner.run_tasks(dispatcher)
        self.assertEqual(runner.SUCCESS, my_runner.finish())

    def test_task_not_picklabe_thread(self):
        t1 = Task("t1", [(my_print, ["out a"])])
        t2 = Task("t2", None, loader=DelayedLoader(
            non_pickable_creator, executed='t1'))
        my_runner = runner.MThreadRunner(self.dep_manager, self.reporter)
        dispatcher = TaskDispatcher({'t1': t1, 't2': t2}, [],
                                     ['t1', 't2'])
        # threaded code have no problems with closures
        my_runner.run_tasks(dispatcher)
        self.assertEqual(runner.SUCCESS, my_runner.finish())
        self.assertEqual(('start', t1), self.reporter.log.pop(0))
        self.assertEqual(('execute', t1), self.reporter.log.pop(0))
        self.assertEqual(('success', t1), self.reporter.log.pop(0))
        self.assertEqual(('start', t2), self.reporter.log.pop(0))
        self.assertEqual(('execute', t2), self.reporter.log.pop(0))
        self.assertEqual(('success', t2), self.reporter.log.pop(0))


# ---------------------------------------------------------------------------
# TestMRunner_execute_task
# ---------------------------------------------------------------------------

@unittest.skipIf(not runner.MRunner.available(), 'MRunner not available')
class TestMRunner_execute_task(DepManagerMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.reporter = FakeReporter()

    def test_hold(self):
        run = runner.MRunner(self.dep_manager, self.reporter)
        task_q = Queue()
        task_q.put(runner.JobHold())  # to test
        task_q.put(None)  # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q,
                                    self.reporter.__class__)
        run.finish()
        # nothing was done
        self.assertTrue(result_q.empty())

    def test_full_task(self):
        # test execute_task_subprocess can receive a full Task object
        run = runner.MRunner(self.dep_manager, self.reporter)
        t1 = Task('t1', [simple_result])
        task_q = Queue()
        task_q.put(runner.JobTask(t1))  # to test
        task_q.put(None)  # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q,
                                    self.reporter.__class__)
        run.finish()
        # check result
        self.assertEqual(result_q.get(),
                         {'name': 't1', 'reporter': 'execute_task'})
        res = result_q.get()
        self.assertEqual(res['task']['result'], 'my-result')
        self.assertTrue(res['task']['executed'])
        self.assertEqual(res['out'], ['success output\n'])
        self.assertEqual(res['err'], ['success error\n'])
        self.assertTrue(result_q.empty())

    def test_full_task_fail(self):
        # test execute_task_subprocess can receive a full Task object
        run = runner.MRunner(self.dep_manager, self.reporter)
        t1 = Task('t1', [simple_fail])
        task_q = Queue()
        task_q.put(runner.JobTask(t1))  # to test
        task_q.put(None)  # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q,
                                    self.reporter.__class__)
        run.finish()
        # check result
        self.assertEqual(result_q.get(),
                         {'name': 't1', 'reporter': 'execute_task'})
        res = result_q.get()
        self.assertEqual(res['name'], 't1')
        self.assertIsInstance(res['failure'], BaseFail)
        self.assertEqual(res['out'], ['simple output\n'])
        self.assertEqual(res['err'], ['simple error\n'])
        # assert result_q.get()['task']['result'] == 'my-result'
        self.assertTrue(result_q.empty())


# ---------------------------------------------------------------------------
# TestMThreadRunner_available
# ---------------------------------------------------------------------------

class TestMThreadRunner_available(unittest.TestCase):
    def test_MThreadRunner_available(self):
        self.assertTrue(runner.MThreadRunner.available())

