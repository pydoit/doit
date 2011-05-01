import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, Task
from doit.control import TaskControl, WaitSelectTask, WaitRunTask



class TestWaitTask(object):

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


class TestAddTask(object):
    def testChangeOrder_AddJustOnce(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(None)
        assert [tasks[1], tasks[0]] == [x for x in tc._add_task(0, 'taskX', False)]
        # both tasks were already added. so no tasks left..
        assert [] == [x for x in tc._add_task(0, 'taskY', False)]

    def testAddNotSelected(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        assert [tasks[1], tasks[0]] == [x for x in tc._add_task(0, 'taskX',False)]

    def testDetectCyclicReference(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None,task_dep=["taskX"])]
        tc = TaskControl(tasks)
        tc.process(None)
        gen = tc._add_task(0, "taskX", False)
        pytest.raises(InvalidDodoFile, gen.next)

    def testParallel(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None)]
        tc = TaskControl(tasks)
        tc.process(None)
        gen1 = tc._add_task(0, "taskX", False)
        assert tasks[1] == gen1.next()
        # gen2 wont get any task, because it was already being processed
        gen2 = tc._add_task(1, "taskY", False)
        pytest.raises(StopIteration, gen2.next)

    def testSetupTasksDontRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next()
        # X is up-to-date
        tasks[0].run_status = 'up-to-date'
        pytest.raises(StopIteration, gen.next)

    def testIncludeSetup(self):
        # with include_setup yield all tasks without waiting for setup tasks to
        # be ready
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', True) # <== include_setup
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        assert tasks[1] == gen.next() # execute setup before
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testSetupTasksRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testWaitSetup(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        # wait for taskX run_status
        wait = gen.next()
        assert wait.task_name == 'taskX'
        assert isinstance(wait, WaitSelectTask)
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

    def testSetupInvalid(self):
        tasks = [Task("taskX",None,setup=["taskZZZZZZZZ"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', False)
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        tasks[0].run_status = 'run' # should be executed
        pytest.raises(InvalidTask, gen.next) # execute setup before

    def testCalcDep(self):
        def get_deps():
            print "gget"
            return {'file_dep': ('a', 'b')}
        tasks = [Task("taskX", None, calc_dep=['task_dep']),
                 Task("task_dep", [(get_deps,)]),
                 ]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc._add_task(0, 'taskX', False)
        assert tasks[1] == gen.next()
        assert isinstance(gen.next(), WaitRunTask)
        tasks[1].execute()
        assert tasks[0] == gen.next()
        assert set(['a', 'b']) == tasks[0].file_dep


class TestGetNext(object):
    def testChangeOrder_AddJustOnce(self):
        tasks = [Task("taskX",None,task_dep=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(None)
        assert [tasks[1], tasks[0]] == [x for x in tc.task_dispatcher()]

    def testAllTasksWaiting(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        gen = tc.task_dispatcher()
        assert tasks[0] == gen.next() # tasks with setup are yield twice
        assert "hold on" == gen.next() # nothing else really available
        tasks[0].run_status = 'run' # should be executed
        assert tasks[1] == gen.next() # execute setup before
        assert tasks[0] == gen.next() # second time, ok
        pytest.raises(StopIteration, gen.next) # nothing left

# TODO get task from waiting queue before new gen

