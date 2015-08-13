import os
import pickle
from multiprocessing import Queue
import platform
import six

import pytest
from mock import Mock

from doit.exceptions import InvalidTask
from doit.dependency import DbmDB, Dependency
from doit.reporter import ConsoleReporter
from doit.task import Task, DelayedLoader
from doit.control import TaskDispatcher, ExecNode
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
    return 'my-result'

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


@pytest.fixture
def reporter(request):
    return FakeReporter()


class TestRunner(object):
    def testInit(self, reporter, dep_manager):
        my_runner = runner.Runner(dep_manager, reporter)
        assert False == my_runner._stop_running
        assert runner.SUCCESS == my_runner.final_result


class TestRunner_SelectTask(object):
    def test_ready(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(dep_manager, reporter)
        assert True == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_DependencyError(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )],
                  file_dep=["i_dont_exist"])
        my_runner = runner.Runner(dep_manager, reporter)
        assert False == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_upToDate(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )], file_dep=[__file__])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.dep_manager.save_success(t1)
        assert False == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert ('up-to-date', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_ignore(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.dep_manager.ignore(t1)
        assert False == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert ('ignore', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_alwaysExecute(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(dep_manager, reporter, always_execute=True)
        my_runner.dep_manager.save_success(t1)
        assert True == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_noSetup_ok(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )])
        my_runner = runner.Runner(dep_manager, reporter)
        assert True == my_runner.select_task(ExecNode(t1, None), {})
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_withSetup(self, reporter, dep_manager):
        t1 = Task("taskX", [(my_print, ["out a"] )], setup=["taskY"])
        my_runner = runner.Runner(dep_manager, reporter)
        # defer execution
        n1 = ExecNode(t1, None)
        assert False == my_runner.select_task(n1, {})
        assert ('start', t1) == reporter.log.pop(0)
        assert not reporter.log
        # trying to select again
        assert True == my_runner.select_task(n1, {})
        assert not reporter.log


    def test_getargs_ok(self, reporter, dep_manager):
        def ok(): return {'x':1}
        def check_x(my_x): return my_x == 1
        t1 = Task('t1', [(ok,)])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', [(check_x,)], getargs={'my_x':('t1','x')})
        n2 = ExecNode(t2, None)
        tasks_dict = {'t1': t1, 't2':t2}
        my_runner = runner.Runner(dep_manager, reporter)

        # t2 gives chance for setup tasks to be executed
        assert False == my_runner.select_task(n2, tasks_dict)
        assert ('start', t2) == reporter.log.pop(0)

        # execute task t1 to calculate value
        assert True == my_runner.select_task(n1, tasks_dict)
        assert ('start', t1) == reporter.log.pop(0)
        t1_result = my_runner.execute_task(t1)
        assert ('execute', t1) == reporter.log.pop(0)
        my_runner.process_task_result(n1, t1_result)
        assert ('success', t1) == reporter.log.pop(0)

        # t2.options are set on select_task
        assert True == my_runner.select_task(n2, tasks_dict)
        assert not reporter.log
        assert {'my_x': 1} == t2.options

    def test_getargs_fail(self, reporter, dep_manager):
        # invalid getargs. Exception wil be raised and task will fail
        def check_x(my_x): return True
        t1 = Task('t1', [lambda :True])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', [(check_x,)], getargs={'my_x':('t1','x')})
        n2 = ExecNode(t2, None)
        tasks_dict = {'t1': t1, 't2':t2}
        my_runner = runner.Runner(dep_manager, reporter)

        # t2 gives chance for setup tasks to be executed
        assert False == my_runner.select_task(n2, tasks_dict)
        assert ('start', t2) == reporter.log.pop(0)

        # execute task t1 to calculate value
        assert True == my_runner.select_task(n1, tasks_dict)
        assert ('start', t1) == reporter.log.pop(0)
        t1_result = my_runner.execute_task(t1)
        assert ('execute', t1) == reporter.log.pop(0)
        my_runner.process_task_result(n1, t1_result)
        assert ('success', t1) == reporter.log.pop(0)

        # select_task t2 fails
        assert False == my_runner.select_task(n2, tasks_dict)
        assert ('fail', t2) == reporter.log.pop(0)
        assert not reporter.log


    def test_getargs_dict(self, reporter, dep_manager):
        def ok(): return {'x':1}
        t1 = Task('t1', [(ok,)])
        n1 = ExecNode(t1, None)
        t2 = Task('t2', None, getargs={'my_x':('t1', None)})
        tasks_dict = {'t1': t1, 't2':t2}
        my_runner = runner.Runner(dep_manager, reporter)
        t1_result = my_runner.execute_task(t1)
        my_runner.process_task_result(n1, t1_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        assert {'my_x': {'x':1}} == t2.options


    def test_getargs_group(self, reporter, dep_manager):
        def ok(): return {'x':1}
        t1 = Task('t1', None, task_dep=['t1:a'], has_subtask=True)
        t1a = Task('t1:a', [(ok,)], is_subtask=True)
        t2 = Task('t2', None, getargs={'my_x':('t1', None)})
        tasks_dict = {'t1': t1, 't1a':t1a, 't2':t2}
        my_runner = runner.Runner(dep_manager, reporter)
        t1a_result = my_runner.execute_task(t1a)
        my_runner.process_task_result(ExecNode(t1a, None), t1a_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        assert {'my_x': {'a':{'x':1}} } == t2.options



    def test_getargs_group_value(self, reporter, dep_manager):
        def ok(): return {'x':1}
        t1 = Task('t1', None, task_dep=['t1:a'], has_subtask=True)
        t1a = Task('t1:a', [(ok,)], is_subtask=True)
        t2 = Task('t2', None, getargs={'my_x':('t1', 'x')})
        tasks_dict = {'t1': t1, 't1a':t1a, 't2':t2}
        my_runner = runner.Runner(dep_manager, reporter)
        t1a_result = my_runner.execute_task(t1a)
        my_runner.process_task_result(ExecNode(t1a, None), t1a_result)

        # t2.options are set on _get_task_args
        my_runner._get_task_args(t2, tasks_dict)
        assert {'my_x': {'a':1} } == t2.options



class TestTask_Teardown(object):
    def test_ok(self, reporter, dep_manager):
        touched = []
        def touch():
            touched.append(1)
        t1 = Task('t1', [], teardown=[(touch,)])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.teardown_list = [t1]
        t1.execute()
        my_runner.teardown()
        assert 1 == len(touched)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_reverse_order(self, reporter, dep_manager):
        def do_nothing():pass
        t1 = Task('t1', [], teardown=[do_nothing])
        t2 = Task('t2', [], teardown=[do_nothing])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.teardown_list = [t1, t2]
        t1.execute()
        t2.execute()
        my_runner.teardown()
        assert ('teardown', t2) == reporter.log.pop(0)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert not reporter.log

    def test_errors(self, reporter, dep_manager):
        def raise_something(x):
            raise Exception(x)
        t1 = Task('t1', [], teardown=[(raise_something,['t1 blow'])])
        t2 = Task('t2', [], teardown=[(raise_something,['t2 blow'])])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.teardown_list = [t1, t2]
        t1.execute()
        t2.execute()
        my_runner.teardown()
        assert ('teardown', t2) == reporter.log.pop(0)
        assert ('cleanup_error',) == reporter.log.pop(0)
        assert ('teardown', t1) == reporter.log.pop(0)
        assert ('cleanup_error',) == reporter.log.pop(0)
        assert not reporter.log


class TestTask_RunAll(object):
    def test_reporter_runtime_error(self, reporter, dep_manager):
        t1 = Task('t1', [], calc_dep=['t2'])
        t2 = Task('t2', [lambda: {'file_dep':[1]}])
        my_runner = runner.Runner(dep_manager, reporter)
        my_runner.run_all(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert runner.ERROR == my_runner.final_result
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)
        assert ('runtime_error',) == reporter.log.pop(0)
        assert not reporter.log


# run tests in both single process runner and multi-process runner
RUNNERS = [runner.Runner, runner.MThreadRunner]
# TODO: test should be added and skipped!
if runner.MRunner.available():
    RUNNERS.append(runner.MRunner)
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
    six.print_(arg1)
def make_args():
    return {'myarg':1}
def action_add_filedep(task, extra_dep):
    task.file_dep.add(extra_dep)


class TestRunner_run_tasks(object):

    def test_teardown(self, reporter, RunnerClass, dep_manager):
        t1 = Task('t1', [], teardown=[ok])
        t2 = Task('t2', [])
        my_runner = RunnerClass(dep_manager, reporter)
        assert [] == my_runner.teardown_list
        my_runner.run_tasks(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        my_runner.finish()
        assert ('teardown', t1) == reporter.log[-1]

    # testing whole process/API
    def test_success(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(my_print, ["out a"] )] )
        t2 = Task("t2", [(my_print, ["out a"] )] )
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0), reporter.log
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)

    # test result, value, out, err are saved into task
    def test_result(self, reporter, RunnerClass, dep_manager):
        task = Task("taskY", [my_action] )
        my_runner = RunnerClass(dep_manager, reporter)
        assert None == task.result
        assert {} == task.values
        assert [None] == [a.out for a in task.actions]
        assert [None] == [a.err for a in task.actions]
        my_runner.run_tasks(TaskDispatcher({'taskY':task}, [], ['taskY']))
        assert runner.SUCCESS == my_runner.finish()
        assert {'bb': 5} == task.result
        assert {'bb': 5} == task.values
        assert ['out here'] == [a.out for a in task.actions]
        assert ['err here'] == [a.err for a in task.actions]

    # whenever a task fails remaining task are not executed
    def test_failureOutput(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [_fail])
        t2 = Task("t2", [_fail])
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert runner.FAILURE == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    def test_error(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [_error])
        t2 = Task("t2", [_error])
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert runner.ERROR == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        # second task is not executed
        assert 0 == len(reporter.log)


    # when successful dependencies are updated
    def test_updateDependencies(self, reporter, RunnerClass, depfile_name):
        depPath = os.path.join(os.path.dirname(__file__), "data", "dependency1")
        ff = open(depPath,"a")
        ff.write("xxx")
        ff.close()
        dependencies = [depPath]

        filePath = os.path.join(os.path.dirname(__file__), "data", "target")
        ff = open(filePath,"a")
        ff.write("xxx")
        ff.close()
        targets = [filePath]

        t1 = Task("t1", [my_print], dependencies, targets)
        dep_manager = Dependency(DbmDB, depfile_name)
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1}, [], ['t1']))
        assert runner.SUCCESS == my_runner.finish()
        d = Dependency(DbmDB, depfile_name)
        assert d._get("t1", os.path.abspath(depPath))


    def test_continue(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(_fail,)] )
        t2 = Task("t2", [(_error,)] )
        t3 = Task("t3", [(ok,)])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        disp = TaskDispatcher({'t1':t1, 't2':t2, 't3':t3}, [], ['t1', 't2', 't3'])
        my_runner.run_tasks(disp)
        assert runner.ERROR == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('fail', t2) == reporter.log.pop(0)
        assert ('start', t3) == reporter.log.pop(0)
        assert ('execute', t3) == reporter.log.pop(0)
        assert ('success', t3) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    def test_continue_dont_execute_parent_of_failed_task(self, reporter,
                                                         RunnerClass, dep_manager):
        t1 = Task("t1", [(_error,)] )
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        t3 = Task("t3", [(ok,)])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        disp = TaskDispatcher({'t1':t1, 't2':t2, 't3':t3}, [], ['t1', 't2', 't3'])
        my_runner.run_tasks(disp)
        assert runner.ERROR == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('fail', t2) == reporter.log.pop(0)
        assert ('start', t3) == reporter.log.pop(0)
        assert ('execute', t3) == reporter.log.pop(0)
        assert ('success', t3) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    def test_continue_dep_error(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(ok,)], file_dep=['i_dont_exist'] )
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        disp = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        my_runner.run_tasks(disp)
        assert runner.ERROR == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('fail', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('fail', t2) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    def test_continue_ignored_dep(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(ok,)], )
        t2 = Task("t2", [(ok,)], task_dep=['t1'])
        my_runner = RunnerClass(dep_manager, reporter, continue_=True)
        my_runner.dep_manager.ignore(t1)
        disp = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        my_runner.run_tasks(disp)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('ignore', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('ignore', t2) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    def test_getargs(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [(use_args,)], getargs=dict(arg1=('t2','myarg')) )
        t2 = Task("t2", [(make_args,)])
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert 0 == len(reporter.log)


    def testActionModifiesFiledep(self, reporter, RunnerClass, dep_manager):
        extra_dep = os.path.join(os.path.dirname(__file__), 'sample_md5.txt')
        t1 = Task("t1", [(my_print, ["out a"] ),
                         (action_add_filedep, (), {'extra_dep': extra_dep})
                     ] )
        my_runner = RunnerClass(dep_manager, reporter)
        my_runner.run_tasks(TaskDispatcher({'t1':t1}, [], ['t1']))
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0), reporter.log
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert t1.file_dep == set([extra_dep])

    # SystemExit runner should not interfere with SystemExit
    def testSystemExitRaises(self, reporter, RunnerClass, dep_manager):
        t1 = Task("t1", [_exit])
        my_runner = RunnerClass(dep_manager, reporter)
        disp = TaskDispatcher({'t1':t1}, [], ['t1'])
        pytest.raises(SystemExit, my_runner.run_tasks, disp)
        my_runner.finish()


@pytest.mark.skipif('not runner.MRunner.available()')
class TestMReporter(object):
    class MyRunner(object):
        def __init__(self):
            self.result_q = Queue()

    def testReporterMethod(self, reporter):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MReporter(fake_runner, reporter)
        my_task = Task("task x", [])
        mp_reporter.add_success(my_task)
        # note limit is 2 seconds because of http://bugs.python.org/issue17707
        got = fake_runner.result_q.get(True, 2)
        assert {'name': "task x", "reporter": 'add_success'} == got

    def testNonReporterMethod(self, reporter):
        fake_runner = self.MyRunner()
        mp_reporter = runner.MReporter(fake_runner, reporter)
        assert hasattr(mp_reporter, 'add_success')
        assert not hasattr(mp_reporter, 'no_existent_method')


class TestJobTask(object):
    def test_closure_is_picklable(self):
        # can pickle because we use cloudpickle
        def non_top_function(): return 4
        t1 = Task('t1', [non_top_function])
        t1p = runner.JobTask(t1).task_pickle
        t2 = pickle.loads(t1p)
        assert 4 == t2.actions[0].py_callable()

    @pytest.mark.xfail('PLAT_IMPL == "PyPy"')  # pypy can handle it :)
    def test_not_picklable_raises_InvalidTask(self):
        # create a large enough recursive obj so pickle fails
        d1 = {}
        last = d1
        for x in range(400):
            dn = {'p': last}
            last = dn
        d1['p'] = last

        def non_top_function(): pass
        t1 = Task('t1', [non_top_function, (d1,)])
        pytest.raises(InvalidTask, runner.JobTask, t1)


# multiprocessing on Windows requires the whole object to be pickable
def test_MRunner_pickable(dep_manager):
    t1 = Task('t1', [])
    import sys
    reporter = ConsoleReporter(sys.stdout, {})
    run = runner.MRunner(dep_manager, reporter)
    run._run_tasks_init(TaskDispatcher({'t1':t1}, [], ['t1']))
    # assert nothing is raised
    pickle.dumps(run)


@pytest.mark.skipif('not runner.MRunner.available()')
class TestMRunner_get_next_job(object):
    # simple normal case
    def test_run_task(self, reporter, dep_manager):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        run = runner.MRunner(dep_manager, reporter)
        run._run_tasks_init(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert t1.name == run.get_next_job(None).name
        assert t2.name == run.get_next_job(None).name
        assert None == run.get_next_job(None)

    def test_stop_running(self, reporter, dep_manager):
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        run = runner.MRunner(dep_manager, reporter)
        run._run_tasks_init(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))
        assert t1.name == run.get_next_job(None).name
        run._stop_running = True
        assert None == run.get_next_job(None)

    def test_waiting(self, reporter, dep_manager):
        t1 = Task('t1', [])
        t2 = Task('t2', [], setup=('t1',))
        run = runner.MRunner(dep_manager, reporter)
        dispatcher = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t2'])
        run._run_tasks_init(dispatcher)

        # first start task 1
        j1 = run.get_next_job(None)
        assert t1.name == j1.name

        # hold until t1 is done
        assert isinstance(run.get_next_job(None), runner.JobHold)
        assert isinstance(run.get_next_job(None), runner.JobHold)

        n1 = dispatcher.nodes[j1.name]
        n1.run_status = 'done'
        j2 = run.get_next_job(n1)
        assert t2.name == j2.name
        assert None == run.get_next_job(dispatcher.nodes[j2.name])


    def test_waiting_controller(self, reporter, dep_manager):
        t1 = Task('t1', [])
        t2 = Task('t2', [], calc_dep=('t1',))
        run = runner.MRunner(dep_manager, reporter)
        run._run_tasks_init(TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2']))

        # first task ok
        assert t1.name == run.get_next_job(None).name

        # hold until t1 finishes
        assert 0 == run.free_proc
        assert isinstance(run.get_next_job(None), runner.JobHold)
        assert 1 == run.free_proc


    def test_delayed_loaded(self, reporter, dep_manager):
        def create():
            return {'basename':'t1', 'actions': None}
        t1 = Task('t1', [], loader=DelayedLoader(create, executed='t2'))
        t2 = Task('t2', [])
        run = runner.MRunner(dep_manager, reporter)
        dispatcher = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        run._run_tasks_init(dispatcher)
        assert t2.name == run.get_next_job(None).name
        assert runner.JobHold.type == run.get_next_job(None).type

        # after t2 is done t1 can be dispatched
        n2 = dispatcher.nodes[t2.name]
        n2.run_status = 'done'
        j1 = run.get_next_job(n2)
        assert t1.name == j1.name
        # the job for t1 contains the whole task since sub-process dont
        # have it
        assert j1.type == runner.JobTask.type



@pytest.mark.skipif('not runner.MRunner.available()')
class TestMRunner_start_process(object):
    # 2 process, 3 tasks
    def test_all_processes(self, reporter, monkeypatch, dep_manager):
        mock_process = Mock()
        monkeypatch.setattr(runner.MRunner, 'Child', mock_process)
        t1 = Task('t1', [])
        t2 = Task('t2', [])
        td = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        run = runner.MRunner(dep_manager, reporter, num_process=2)
        run._run_tasks_init(td)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 2 == len(proc_list)
        assert t1.name == task_q.get().name
        assert t2.name == task_q.get().name


    # 2 process, 1 task
    def test_less_processes(self, reporter, monkeypatch, dep_manager):
        mock_process = Mock()
        monkeypatch.setattr(runner.MRunner, 'Child', mock_process)
        t1 = Task('t1', [])
        td = TaskDispatcher({'t1':t1}, [], ['t1'])
        run = runner.MRunner(dep_manager, reporter, num_process=2)
        run._run_tasks_init(td)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 1 == len(proc_list)
        assert t1.name == task_q.get().name


    # 2 process, 2 tasks (but only one task can be started)
    def test_waiting_process(self, reporter, monkeypatch, dep_manager):
        mock_process = Mock()
        monkeypatch.setattr(runner.MRunner, 'Child', mock_process)
        t1 = Task('t1', [])
        t2 = Task('t2', [], task_dep=['t1'])
        td = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        run = runner.MRunner(dep_manager, reporter, num_process=2)
        run._run_tasks_init(td)
        result_q = Queue()
        task_q = Queue()

        proc_list = run._run_start_processes(task_q, result_q)
        run.finish()
        assert 2 == len(proc_list)
        assert t1.name == task_q.get().name
        assert isinstance(task_q.get(), runner.JobHold)


def non_pickable_creator():
    return {'basename': 't2', 'actions': [lambda: True]}

class TestMRunner_parallel_run_tasks(object):

    @pytest.mark.skipif('not runner.MRunner.available()')
    def test_task_cloudpicklabe_multiprocess(self, reporter, dep_manager):
        t1 = Task("t1", [(my_print, ["out a"] )] )
        t2 = Task("t2", None, loader=DelayedLoader(
            non_pickable_creator, executed='t1'))
        my_runner = runner.MRunner(dep_manager, reporter)
        dispatcher = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        my_runner.run_tasks(dispatcher)
        assert runner.SUCCESS == my_runner.finish()

    def test_task_not_picklabe_thread(self, reporter, dep_manager):
        t1 = Task("t1", [(my_print, ["out a"] )] )
        t2 = Task("t2", None, loader=DelayedLoader(
            non_pickable_creator, executed='t1'))
        my_runner = runner.MThreadRunner(dep_manager, reporter)
        dispatcher = TaskDispatcher({'t1':t1, 't2':t2}, [], ['t1', 't2'])
        # threaded code have no problems with closures
        my_runner.run_tasks(dispatcher)
        assert runner.SUCCESS == my_runner.finish()
        assert ('start', t1) == reporter.log.pop(0), reporter.log
        assert ('execute', t1) == reporter.log.pop(0)
        assert ('success', t1) == reporter.log.pop(0)
        assert ('start', t2) == reporter.log.pop(0)
        assert ('execute', t2) == reporter.log.pop(0)
        assert ('success', t2) == reporter.log.pop(0)



@pytest.mark.skipif('not runner.MRunner.available()')
class TestMRunner_execute_task(object):
    def test_hold(self, reporter, dep_manager):
        run = runner.MRunner(dep_manager, reporter)
        task_q = Queue()
        task_q.put(runner.JobHold()) # to test
        task_q.put(None) # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q, reporter.__class__)
        run.finish()
        # nothing was done
        assert result_q.empty()

    def test_full_task(self, reporter, dep_manager):
        # test execute_task_subprocess can receive a full Task object
        run = runner.MRunner(dep_manager, reporter)
        t1 = Task('t1', [simple_result])
        task_q = Queue()
        task_q.put(runner.JobTask(t1)) # to test
        task_q.put(None) # to terminate function
        result_q = Queue()
        run.execute_task_subprocess(task_q, result_q, reporter.__class__)
        run.finish()
        # check result
        assert result_q.get() == {'name': 't1', 'reporter': 'execute_task'}
        assert result_q.get()['task']['result'] == 'my-result'
        assert result_q.empty()



def test_MThreadRunner_available():
    assert runner.MThreadRunner.available() == True
