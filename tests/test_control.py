from collections import deque
import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, Task
from doit.control import TaskControl, TaskDispatcher, ExecNode, no_none



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

    def test_userErrorSetupTask(self):
        tasks = [Task('wrong', None, setup=["typo"])]
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
        t1 = Task("taskX", None, file_dep=[], targets=['intermediate'])
        t2 = Task("taskY", None, file_dep=['intermediate'], task_dep=['taskZ'])
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

    def testProcessSelection(self):
        filter_ = ['t2', 't3']
        tc = TaskControl(TASKS_SAMPLE)
        tc.process(filter_)
        assert filter_ == tc.selected_tasks

    def testProcessAll(self):
        tc = TaskControl(TASKS_SAMPLE)
        tc.process(None)
        assert ['t1', 't2', 'g1', 'g1.a', 'g1.b', 't3'] == tc.selected_tasks

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


class TestExecNode(object):
    def test_repr(self):
        node = ExecNode(Task('t1', None), None)
        assert 't1' in repr(node)

    def test_ready_select__not_waiting(self):
        task = Task("t1", None)
        node = ExecNode(task, None)
        assert False == node.wait_select

    def test_step(self):
        def my_gen():
            yield 1
            yield 2
        task = Task("t1", None)
        node = ExecNode(task, None)
        node.generator = my_gen()
        assert 1 == node.step()
        assert 2 == node.step()
        assert None == node.step()


class TestDecoratorNoNone(object):
    def test_filtering(self):
        def my_gen():
            yield 1
            yield None
            yield 2
        gen = no_none(my_gen)
        assert [1, 2] == [x for x in gen()]


class TestTaskDispatcher_GenNone(object):
    def test_create(self):
        tasks = {'t1': Task('t1', None)}
        td = TaskDispatcher(tasks, [])
        node = td._gen_node(None, 't1')
        assert isinstance(node, ExecNode)
        assert node == td.nodes['t1']

    def test_already_created(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None)
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        td._gen_node(n1, 't2')
        assert None == td._gen_node(None, 't1')

    def test_cyclic(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None)
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(n1, 't2')
        pytest.raises(InvalidDodoFile, td._gen_node, n2, 't1')



class TestTaskDispatcher_node_add_wait_run(object):
    def test_wait(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n1.wait_run.add('xxx')
        td._node_add_wait_run(n1, ['t2'])
        assert 2 == len(n1.wait_run)
        assert 't2' in n1.wait_run
        assert n1 in n2.waiting_me

    def test_none(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        node = td._gen_node(None, 't1')
        tasks['t2'].run_status = 'done'
        td._node_add_wait_run(node, ['t2'])
        assert not node.wait_run


class TestTaskDispatcher_add_task(object):
    def test_no_deps(self):
        tasks = {'t1': Task('t1', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        assert [tasks['t1']] == list(td._add_task(n1))

    def test_task_deps(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2', 't3']),
                 't2': Task('t2', None),
                 't3': Task('t3', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)
        assert tasks['t2'] == gen.next().task
        assert tasks['t3'] == gen.next().task
        assert 'wait' == gen.next()
        tasks['t2'].run_status = 'done'
        td._update_waiting(tasks['t2'])
        tasks['t3'].run_status = 'done'
        td._update_waiting(tasks['t3'])
        assert tasks['t1'] == gen.next()

    def test_task_deps_already_created(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        td._gen_node(None, 't2')
        gen = td._add_task(n1)
        assert 'wait' == gen.next()
        tasks['t2'].run_status = 'done'
        td._update_waiting(tasks['t2'])
        assert tasks['t1'] == gen.next()

    def test_task_deps_no_wait(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        td._gen_node(None, 't2')
        tasks['t2'].run_status = 'done'
        gen = td._add_task(n1)
        assert tasks['t1'] == gen.next()

    def test_calc_dep(self):
        def calc_intermediate():
            return {'file_dep': ['intermediate']}
        tasks = {'t1': Task('t1', None, calc_dep=['t2']),
                 't2': Task('t2', [calc_intermediate]),
                 't3': Task('t3', None, targets=['intermediate']),
                 }
        td = TaskDispatcher(tasks, {'intermediate': 't3'})
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)
        assert tasks['t2'] == gen.next().task
        assert 'wait' == gen.next()
        # execute t2 to process calc_dep
        tasks['t2'].execute()
        tasks['t2'].run_status = 'done'
        td._update_waiting(tasks['t2'])
        got = gen.next()
        assert 'intermediate' in tasks['t1'].file_dep
        assert 't3' in tasks['t1'].task_dep
        assert tasks['t3'] == got.task

        # t3 was added by calc dep
        assert 'wait' == gen.next()
        tasks['t3'].run_status = 'done'
        td._update_waiting(tasks['t3'])
        assert tasks['t1'] == gen.next()


    def test_setup_task__run(self):
        tasks = {'t1': Task('t1', None, setup=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)
        assert tasks['t1'] == gen.next() # first time (just select)
        assert 'wait' == gen.next()      # wait for select result
        tasks['t1'].run_status = 'run'
        assert tasks['t2'] == gen.next().task # send setup task
        assert 'wait' == gen.next()
        assert tasks['t1'] == gen.next()  # second time


class TestTaskDispatcher_get_next_node(object):
    def test_none(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        assert None == td._get_next_node([], [])

    def test_ready(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        ready = deque([n1])
        assert n1 == td._get_next_node(ready, ['t2'])
        assert 0 == len(ready)

    def test_to_run(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        to_run = ['t2', 't1']
        td._gen_node(None, 't1') # t1 was already created
        got = td._get_next_node([], to_run)
        assert isinstance(got, ExecNode)
        assert 't2' == got.task.name
        assert [] == to_run

    def test_to_run_none(self):
        tasks = {'t1': Task('t1', None),
                 }
        td = TaskDispatcher(tasks, [])
        td._gen_node(None, 't1') # t1 was already created
        to_run = ['t1']
        assert None == td._get_next_node([], to_run)
        assert [] == to_run


class TestTaskDispatcher_update_waiting(object):
    def test_wait_select(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n2 = td._gen_node(None, 't2')
        n2.wait_select = True
        n2.task.run_status = 'run'
        td.waiting.add(n2)
        td._update_waiting(n2.task)
        assert False == n2.wait_select
        assert deque([n2]) == td.ready

    def test_wait_run(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [])
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        td._node_add_wait_run(n1, ['t2'])
        n2.task.run_status = 'done'
        td.waiting.add(n1)
        td._update_waiting(n2.task)
        assert deque([n1]) == td.ready
        assert 0 == len(td.waiting)


class TestTaskDispatcher_dispatcher_generator(object):
    def test_normal(self):
        tasks = [Task("t1", None, task_dep=["t2"]),
                 Task("t2", None,)]
        control = TaskControl(tasks)
        control.process(['t1'])
        gen = control.task_dispatcher()

        assert tasks[1] == gen.next()
        assert "hold on" == gen.next()
        assert "hold on" == gen.next() # hold until t2 is done
        tasks[1].run_status = 'done'
        assert tasks[0] == gen.send(tasks[1])
        pytest.raises(StopIteration, gen.next)

    def test_include_setup(self):
        tasks = [Task("t1", None, task_dep=["t2"]),
                 Task("t2", None,)]
        control = TaskControl(tasks)
        control.process(['t1'])
        gen = control.task_dispatcher(include_setup=True)
        # dont wait for tasks
        assert tasks[0] == gen.send(None)
        assert tasks[1] == gen.send(None)
        pytest.raises(StopIteration, gen.send, None)
