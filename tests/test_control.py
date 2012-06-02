import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, Task
from doit.control import TaskControl, TaskDispatcher
from doit.control import WaitSelectTask, WaitRunTask



class TestWaitTask(object):

    def test_repr(self):
        wait_task = WaitRunTask('a', 'b')
        assert "<WaitRunTask waiting=a wait_for=b>" == repr(wait_task)

    def test_wait_select_ready(self):
        assert WaitRunTask.ready('up-to-date')
        assert not WaitRunTask.ready(None)

    def test_wait_run_ready(self):
        assert WaitRunTask.ready('done')
        assert WaitRunTask.ready('up-to-date')
        assert not WaitRunTask.ready('whatever')



class TestTaskControlInit(object):

    def test_addTask(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None)
        tc = TaskControl([t1, t2])
        assert 2 == len(tc.tasks)

    def test_targetDependency(self):
        t1 = Task("taskX", None,[],['intermediate'])
        t2 = Task("taskY", None,['intermediate'],[])
        TaskControl([t1, t2])
        assert ['taskX'] == t2.task_dep

    # 2 tasks can not have the same name
    def test_addTaskSameName(self):
        t1 = Task("taskX", None)
        t2 = Task("taskX", None)
        pytest.raises(InvalidDodoFile, TaskControl, [t1, t2])

    def test_addInvalidTask(self):
        pytest.raises(InvalidTask, TaskControl, [666])

    def test_userErrorTaskDependency(self):
        tasks = [Task('wrong', None, task_dep=["typo"])]
        pytest.raises(InvalidTask, TaskControl, tasks)

    def test_sameTarget(self):
        tasks = [Task('t1',None,[],["fileX"]),
                 Task('t2',None,[],["fileX"])]
        pytest.raises(InvalidTask, TaskControl, tasks)


    def test_wild(self):
        tasks = [Task('t1',None, task_dep=['foo*']),
                 Task('foo4',None,)]
        TaskControl(tasks)
        assert 'foo4' in tasks[0].task_dep

    def test_bug770150_task_dependency_from_target(self):
        t1 = Task("taskX", None,[],['intermediate'])
        t2 = Task("taskY", None,['intermediate'], task_dep=['taskZ'])
        t3 = Task("taskZ", None)
        TaskControl([t1, t2, t3])
        assert ['taskZ', 'taskX'] == t2.task_dep


TASKS_SAMPLE = [Task("t1", [""], doc="t1 doc string"),
                Task("t2", [""], doc="t2 doc string"),
                Task("g1", None, doc="g1 doc string"),
                Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
                Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
                Task("t3", [""], doc="t3 doc string",
                     params=[{'name':'opt1','long':'message','default':''}])]


class TestTaskControlCmdOptions(object):
    def testFilter(self):
        filter_ = ['t2', 't3']
        tc = TaskControl(TASKS_SAMPLE)
        assert filter_ == tc._filter_tasks(filter_)

    def testProcess(self):
        filter_ = ['t2', 't3']
        tc = TaskControl(TASKS_SAMPLE)
        tc.process(filter_)
        assert filter_ == tc.selected_tasks

    def testFilterPattern(self):
        tc = TaskControl(TASKS_SAMPLE)
        assert ['t1', 'g1', 'g1.a', 'g1.b'] == tc._filter_tasks(['*1*'])

    def testFilterSubtask(self):
        filter_ = ["t1", "g1.b"]
        tc =  TaskControl(TASKS_SAMPLE)
        assert filter_ == tc._filter_tasks(filter_)

    def testFilterTarget(self):
        tasks = list(TASKS_SAMPLE)
        tasks.append(Task("tX", [""],[],["targetX"]))
        tc =  TaskControl(tasks)
        assert ['tX'] == tc._filter_tasks(["targetX"])

    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        tc =  TaskControl(TASKS_SAMPLE)
        pytest.raises(InvalidCommand, tc._filter_tasks, ['no'])

    def testFilterEmptyList(self):
        filter_ = []
        tc = TaskControl(TASKS_SAMPLE)
        assert filter_ == tc._filter_tasks(filter_)

    def testOptions(self):
        options = ["t3", "--message", "hello option!", "t1"]
        tc = TaskControl(TASKS_SAMPLE)
        assert ['t3', 't1'] == tc._filter_tasks(options)
        assert "hello option!" == tc.tasks['t3'].options['opt1']


def create_dispatcher(task_list, selection=None):
    control = TaskControl(task_list)
    control.process(selection)
    return TaskDispatcher(control.tasks, control.targets, control.selected_tasks)

class TestAddTask(object):
    def testChangeOrder_AddJustOnce(self):
        tasks = [Task("taskX", None, task_dep=["taskY"]),
                 Task("taskY", None,)]
        td = create_dispatcher(tasks)
        gen = td._add_task(0, 'taskX', False)
        assert tasks[1] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        assert tasks[0] == gen.next()
        pytest.raises(StopIteration, gen.next)
        # both tasks were already added. so no tasks left..
        assert [] == [x for x in td._add_task(0, 'taskY', False)]

    def testAddNotSelected(self):
        tasks = [Task("taskX", None, task_dep=["taskY"]),
                 Task("taskY", None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[1] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        assert tasks[0] == gen.next()

    def testDetectCyclicReference(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None,task_dep=["taskX"])]
        td = create_dispatcher(tasks)
        gen = td._add_task(0, "taskX", False)
        pytest.raises(InvalidDodoFile, gen.next)

    def testParallelExecuteOnlyOnce(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None)]
        td = create_dispatcher(tasks)
        gen1 = td._add_task(0, "taskX", False)
        assert tasks[1] == gen1.next()
        # gen2 wont get any task, because it was already being processed
        gen2 = td._add_task(1, "taskY", False)
        pytest.raises(StopIteration, gen2.next)

    def testParallelWaitTaskDep(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None)]
        td = create_dispatcher(tasks)
        gen1 = td._add_task(0, "taskX", False)
        assert tasks[1] == gen1.next()
        # wait for taskY to finish
        wait = gen1.next()
        assert wait.wait_for == 'taskY'
        assert isinstance(wait, WaitRunTask)
        assert tasks[0] == gen1.next()
        pytest.raises(StopIteration, gen1.next)

    def testSetupTasksDontRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next()
        # X is up-to-date
        tasks[0].run_status = 'up-to-date'
        pytest.raises(StopIteration, gen.next)

    def testSetupTasksRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert isinstance(gen.next(), WaitRunTask)
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testWaitSetupSelect(self):
        tasks = [Task("taskX", None, setup=["taskY"]),
                 Task("taskY", None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        # wait for taskX run_status
        wait = gen.next()
        assert wait.wait_for == 'taskX'
        assert isinstance(wait, WaitSelectTask)
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert isinstance(gen.next(), WaitRunTask)
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testWaitSetupRun(self):
        tasks = [Task("taskX", None, setup=["taskY"]),
                 Task("taskY",None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        # wait for taskX run_status
        wait = gen.next()
        assert wait.wait_for == 'taskX'
        assert isinstance(wait, WaitSelectTask)
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        # wait execution finish
        wait2 = gen.next()
        assert wait2.wait_for == 'taskY'
        assert isinstance(wait2, WaitRunTask)
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testSetupInvalid(self):
        tasks = [Task("taskX",None,setup=["taskZZZZZZZZ"]),
                 Task("taskY",None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        tasks[0].run_status = 'run' # should be executed
        pytest.raises(InvalidTask, gen.next) # execute setup before

    def testCalcDep(self):
        def get_deps():
            return {'file_dep': ('a', 'b')}
        tasks = [Task("taskX", None, calc_dep=['task_dep']),
                 Task("task_dep", [(get_deps,)]),
                 ]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[1] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        tasks[1].execute()
        assert tasks[0] == gen.next()
        assert set(['a', 'b']) == tasks[0].file_dep

    def testCalcDepFileDepImplicitTaskDep(self):
        # if file_dep is a target from another task, this other task
        # should be a task_dep
        def get_deps():
            return {'file_dep': ('a', 'b')}
        tasks = [Task("taskX", None, calc_dep=['task_dep']),
                 Task("task_dep", [(get_deps,)]),
                 Task("create_dep", None, targets=['a']),
                 ]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td._add_task(0, 'taskX', False)
        assert tasks[1] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        tasks[1].execute()
        # need to create file_dep first
        assert tasks[2] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        assert tasks[0] == gen.next()
        assert set(['a', 'b']) == tasks[0].file_dep
        assert ['create_dep'] == tasks[0].task_dep

class TestGetNext(object):
    def testChangeOrder_AddJustOnce(self):
        tasks = [Task("taskX", None, task_dep=["taskY"]),
                 Task("taskY", None,)]
        td = create_dispatcher(tasks)
        gen = td.dispatcher_generator()
        assert tasks[1] == gen.next()
        assert "hold on" == gen.next()
        tasks[1].run_status = "done"
        assert tasks[0] == gen.next()
        pytest.raises(StopIteration, gen.next) # nothing left

    def testAllTasksWaiting(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td.dispatcher_generator()
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        assert "hold on" == gen.next() # nothing else really available
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert "hold on" == gen.next()
        tasks[1].run_status = 'done' # should be executed
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testAllTasksWaiting2(self):
        tasks = [Task("task0", None,),
                 Task("taskX", None, task_dep=["task0"]),
                 Task("taskY", None, task_dep=["task0"])]
        td = create_dispatcher(tasks, ['taskX', 'taskY'])
        gen = td.dispatcher_generator()
        assert tasks[0] == gen.next()
        assert "hold on" == gen.next() # nothing else really available
        tasks[0].run_status = 'done' # should be executed
        assert tasks[1] == gen.next()
        assert tasks[2] == gen.next()
        pytest.raises(StopIteration, gen.next) # nothing left


    def testIncludeSetup(self):
        # with include_setup yield all tasks without waiting for setup tasks to
        # be ready
        tasks = [Task("taskX", None, setup=["taskY"]),
                 Task("taskY", None,)]
        td = create_dispatcher(tasks, ['taskX'])
        gen = td.dispatcher_generator(True) # <== include_setup
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        assert tasks[1] == gen.next() # execute setup before
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

