from collections import deque

import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import Stream, InvalidTask, Task, DelayedLoader
from doit.control import TaskControl, TaskDispatcher, ExecNode
from doit.control import no_none



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
                Task("g1.a", [""], doc="g1.a doc string", subtask_of='g1'),
                Task("g1.b", [""], doc="g1.b doc string", subtask_of='g1'),
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

    def test_filter_delayed_subtask(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None, loader=DelayedLoader(lambda: None))
        control = TaskControl([t1, t2])
        control._filter_tasks(['taskY:foo'])
        assert isinstance(t2.loader, DelayedLoader)
        # sub-task will use same loader, and keep parent basename
        assert control.tasks['taskY:foo'].loader.basename == 'taskY'
        assert control.tasks['taskY:foo'].loader is t2.loader

    def test_filter_delayed_regex_single(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None,
                  loader=DelayedLoader(lambda: None, target_regex='a.*'))
        t3 = Task("taskZ", None,
                  loader=DelayedLoader(lambda: None, target_regex='b.*'))
        t4 = Task("taskW", None,
                  loader=DelayedLoader(lambda: None))
        control = TaskControl([t1, t2, t3, t4], auto_delayed_regex=False)
        selected = control._filter_tasks(['abc'])
        assert isinstance(t2.loader, DelayedLoader)
        assert len(selected) == 1
        assert selected[0] == '_regex_target_abc:taskY'
        sel_task = control.tasks['_regex_target_abc:taskY']
        assert sel_task.file_dep == {'abc'}
        assert sel_task.loader.basename == 'taskY'
        assert sel_task.loader is t2.loader

    def test_filter_delayed_multi_select(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None,
                  loader=DelayedLoader(lambda: None, target_regex='a.*'))
        t3 = Task("taskZ", None,
                  loader=DelayedLoader(lambda: None, target_regex='b.*'))
        t4 = Task("taskW", None,
                  loader=DelayedLoader(lambda: None))
        control = TaskControl([t1, t2, t3, t4], auto_delayed_regex=False)
        selected = control._filter_tasks(['abc', 'att'])
        assert isinstance(t2.loader, DelayedLoader)
        assert len(selected) == 2
        assert selected[0] == '_regex_target_abc:taskY'
        assert selected[1] == '_regex_target_att:taskY'

    def test_filter_delayed_regex_multiple_match(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None,
                  loader=DelayedLoader(lambda: None, target_regex='a.*'))
        t3 = Task("taskZ", None,
                  loader=DelayedLoader(lambda: None, target_regex='ab.'))
        t4 = Task("taskW", None,
                  loader=DelayedLoader(lambda: None))
        control = TaskControl([t1, t2, t3, t4], auto_delayed_regex=False)
        selected = control._filter_tasks(['abc'])
        assert len(selected) == 2
        assert (sorted(selected) ==
                ['_regex_target_abc:taskY', '_regex_target_abc:taskZ'])
        assert control.tasks['_regex_target_abc:taskY'].file_dep == {'abc'}
        assert control.tasks['_regex_target_abc:taskZ'].file_dep == {'abc'}
        assert (control.tasks['_regex_target_abc:taskY'].loader.basename ==
                t2.name)
        assert (control.tasks['_regex_target_abc:taskZ'].loader.basename ==
                t3.name)

    def test_filter_delayed_regex_auto(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None,
                  loader=DelayedLoader(lambda: None, target_regex='a.*'))
        t3 = Task("taskZ", None,
                  loader=DelayedLoader(lambda: None))
        control = TaskControl([t1, t2, t3], auto_delayed_regex=True)
        selected = control._filter_tasks(['abc'])
        assert len(selected) == 2
        assert (sorted(selected) ==
                ['_regex_target_abc:taskY', '_regex_target_abc:taskZ'])
        assert control.tasks['_regex_target_abc:taskY'].file_dep == {'abc'}
        assert control.tasks['_regex_target_abc:taskZ'].file_dep == {'abc'}
        assert (control.tasks['_regex_target_abc:taskY'].loader.basename ==
                t2.name)
        assert (control.tasks['_regex_target_abc:taskZ'].loader.basename ==
                t3.name)


    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        tc =  TaskControl(TASKS_SAMPLE)
        pytest.raises(InvalidCommand, tc._filter_tasks, ['no'])

    def testFilterWrongSubtaskName(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None)
        tc =  TaskControl([t1, t2])
        pytest.raises(InvalidCommand, tc._filter_tasks, ['taskX:no'])

    def testFilterEmptyList(self):
        filter_ = []
        tc = TaskControl(TASKS_SAMPLE)
        assert filter_ == tc._filter_tasks(filter_)

    def testOptions(self):
        options = ["t3", "--message", "hello option!", "t1"]
        tc = TaskControl(TASKS_SAMPLE)
        assert ['t3', 't1'] == tc._filter_tasks(options)
        assert "hello option!" == tc.tasks['t3'].options['opt1']

    def testPosParam(self):
        tasks = list(TASKS_SAMPLE)
        tasks.append(Task("tP", [""],[],[], pos_arg='myp'))
        tc = TaskControl(tasks)
        args = ["tP", "hello option!", "t1"]
        assert ['tP',] == tc._filter_tasks(args)
        assert ["hello option!", "t1"] == tc.tasks['tP'].pos_arg_val


class TestExecNode(object):
    def test_repr(self):
        node = ExecNode(Task('t1', None), None)
        assert 't1' in repr(node)

    def test_ready_select__not_waiting(self):
        task = Task("t1", None)
        node = ExecNode(task, None)
        assert False == node.wait_select

    def test_parent_status_failure(self):
        n1 = ExecNode(Task('t1', None), None)
        n2 = ExecNode(Task('t2', None), None)
        n1.run_status = 'failure'
        n2.parent_status(n1)
        assert [n1] == n2.bad_deps
        assert [] == n2.ignored_deps

    def test_parent_status_ignore(self):
        n1 = ExecNode(Task('t1', None), None)
        n2 = ExecNode(Task('t2', None), None)
        n1.run_status = 'ignore'
        n2.parent_status(n1)
        assert [] == n2.bad_deps
        assert [n1] == n2.ignored_deps


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
        td = TaskDispatcher(tasks, [], None)
        node = td._gen_node(None, 't1')
        assert isinstance(node, ExecNode)
        assert node == td.nodes['t1']

    def test_already_created(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None)
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        td._gen_node(n1, 't2')
        assert None == td._gen_node(None, 't1')

    def test_cyclic(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None)
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(n1, 't2')
        pytest.raises(InvalidDodoFile, td._gen_node, n2, 't1')



class TestTaskDispatcher_node_add_wait_run(object):
    def test_wait(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n1.wait_run.add('xxx')
        td._node_add_wait_run(n1, ['t2'])
        assert 2 == len(n1.wait_run)
        assert 't2' in n1.wait_run
        assert not n1.bad_deps
        assert n1 in n2.waiting_me

    def test_none(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n2.run_status = 'done'
        td._node_add_wait_run(n1, ['t2'])
        assert not n1.wait_run

    def test_deps_not_ok(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n2.run_status = 'failure'
        td._node_add_wait_run(n1, ['t2'])
        assert n1.bad_deps

    def test_calc_dep_already_executed(self):
        tasks = {'t1': Task('t1', None, calc_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n2.run_status = 'done'
        n2.task.values = {'calc_dep': ['t3'], 'task_dep':['t5']}
        td._node_add_wait_run(n1, ['t2'], calc=True)
        # n1 is updated with results from t2
        assert n1.calc_dep == set(['t2', 't3'])
        assert n1.task_dep == ['t5']
        # n1 doesnt need to wait any calc_dep to be executed
        assert n1.wait_run_calc == set()


class TestTaskDispatcher_add_task(object):
    def test_no_deps(self):
        tasks = {'t1': Task('t1', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        assert [tasks['t1']] == list(td._add_task(n1))

    def test_task_deps(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2', 't3']),
                 't2': Task('t2', None),
                 't3': Task('t3', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)
        n2 = next(gen)
        assert tasks['t2'] == n2.task
        n3 = next(gen)
        assert tasks['t3'] == n3.task
        assert 'wait' == next(gen)
        tasks['t2'].run_status = 'done'
        td._update_waiting(n2)
        tasks['t3'].run_status = 'done'
        td._update_waiting(n3)
        assert tasks['t1'] == next(gen)

    def test_task_deps_already_created(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        assert 'wait' == n1.step()
        assert 'wait' == n1.step()
        #tasks['t2'].run_status = 'done'
        td._update_waiting(n2)
        assert tasks['t1'] == n1.step()

    def test_task_deps_no_wait(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n2.run_status = 'done'
        gen = td._add_task(n1)
        assert tasks['t1'] == next(gen)

    def test_calc_dep(self):
        def calc_intermediate():
            return {'file_dep': ['intermediate']}
        tasks = {'t1': Task('t1', None, calc_dep=['t2']),
                 't2': Task('t2', [calc_intermediate]),
                 't3': Task('t3', None, targets=['intermediate']),
                 }
        td = TaskDispatcher(tasks, {'intermediate': 't3'}, None)
        n1 = td._gen_node(None, 't1')
        n2 = n1.step()
        assert tasks['t2'] == n2.task
        assert 'wait' == n1.step()
        # execute t2 to process calc_dep
        tasks['t2'].execute(Stream(0))
        td.nodes['t2'].run_status = 'done'
        td._update_waiting(n2)
        n3 = n1.step()
        assert tasks['t3'] == n3.task
        assert 'intermediate' in tasks['t1'].file_dep
        assert 't3' in tasks['t1'].task_dep

        # t3 was added by calc dep
        assert 'wait' == n1.step()
        n3.run_status = 'done'
        td._update_waiting(n3)
        assert tasks['t1'] == n1.step()


    def test_calc_dep_already_executed(self):
        tasks = {'t1': Task('t1', None, calc_dep=['t2']),
                 't2': Task('t2', None),
                 't3': Task('t3', None),
                 }
        td = TaskDispatcher(tasks, {'intermediate': 't3'}, None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        n2.run_status = 'done'
        n2.task.values = {'calc_dep': ['t3']}
        assert 't3' == n1.step().task.name
        assert set() == n1.wait_run
        assert set() == n1.wait_run_calc
        #assert False


    def test_setup_task__run(self):
        tasks = {'t1': Task('t1', None, setup=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)
        assert tasks['t1'] == next(gen) # first time (just select)
        assert 'wait' == next(gen)      # wait for select result
        n1.run_status = 'run'
        assert tasks['t2'] == next(gen).task # send setup task
        assert 'wait' == next(gen)
        assert tasks['t1'] == next(gen)  # second time


    def test_delayed_creation(self):
        def creator():
            yield Task('foo', None, loader=DelayedLoader(lambda : None))
        delayed_loader = DelayedLoader(creator, executed='t2')
        tasks = {'t1': Task('t1', None, loader=delayed_loader),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        gen = td._add_task(n1)

        # first returned node is `t2` because it is an implicit task_dep
        n2 = next(gen)
        assert n2.task.name == 't2'

        # wait until t2 is finished
        n3 = next(gen)
        assert n3 == 'wait'

        # after t2 is done, generator is reseted
        td._update_waiting(n2)
        n4 = next(gen)
        assert n4 == "reset generator"

        # recursive loader is preserved
        assert isinstance(td.tasks['foo'].loader, DelayedLoader)
        pytest.raises(AssertionError, next, gen)


    def test_delayed_creation_sub_task(self):
        # usually a repeated loader is replaced by the real task
        # when it is first executed, the problem arises when the
        # the expected task is not actually created
        def creator():
            yield Task('t1:foo', None)
            yield Task('t1:bar', None)
        delayed_loader = DelayedLoader(creator, executed='t2')
        tasks = {
            't1': Task('t1', None, loader=delayed_loader),
            't2': Task('t2', None),}

        # simulate a sub-task from delayed created added to task_list
        tasks['t1:foo'] = Task('t1:foo', None, loader=delayed_loader)
        tasks['t1:xxx'] = Task('t1:xxx', None, loader=delayed_loader)
        delayed_loader.basename = 't1'

        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1:foo')
        gen = td._add_task(n1)

        # first returned node is `t2` because it is an implicit task_dep
        n1b = next(gen)
        assert n1b.task.name == 't2'

        # wait until t2 is finished
        n1c = next(gen)
        assert n1c == 'wait'

        # after t2 is done, generator is reseted
        n1b.run_status = 'successful'
        td._update_waiting(n1b)
        n1d = next(gen)
        assert n1d == "reset generator"
        assert 't1:foo' in td.tasks
        assert 't1:bar' in td.tasks

        # finish with t1:foo
        gen2 = td._add_task(n1)
        n1.reset_task(td.tasks[n1.task.name], gen2)
        n2 = next(gen2)
        assert n2.name == 't1:foo'
        pytest.raises(StopIteration, next, gen2)

        # try non-existent t1:xxx
        n3 = td._gen_node(None, 't1:xxx')
        gen3 = td._add_task(n3)
        # ? should raise a runtime error?
        assert next(gen3) == 'reset generator'


    def test_delayed_creation_target_regex(self):
        def creator():
            yield Task('foo', None, targets=['tgt1'])
        delayed_loader = DelayedLoader(creator,
                                       executed='t2', target_regex='tgt1')
        tasks = {
            't1': Task('t1', None, loader=delayed_loader),
            't2': Task('t2', None),
        }

        tc = TaskControl(list(tasks.values()))
        selection = tc._filter_tasks(['tgt1'])
        assert ['_regex_target_tgt1:t1'] == selection
        td = TaskDispatcher(tc.tasks, tc.targets, selection)

        n1 = td._gen_node(None, '_regex_target_tgt1:t1')
        gen = td._add_task(n1)

        # first returned node is `t2` because it is an implicit task_dep
        n2 = next(gen)
        assert n2.task.name == 't2'

        # wait until t2 is finished
        n3 = next(gen)
        assert n3 == 'wait'

        # after t2 is done, generator is reseted
        n2.run_status = 'done'
        td._update_waiting(n2)
        n4 = next(gen)
        assert n4 == "reset generator"

        # manually reset generator
        n1.reset_task(td.tasks[n1.task.name], td._add_task(n1))

        # get the delayed created task
        gen2 = n1.generator  # n1 generator was reset / replaced
        # get t1 because of its target was a file_dep of _regex_target_tgt1
        n5 = next(gen2)
        assert n5.task.name == 'foo'

        # get internal created task
        n5.run_status = 'done'
        td._update_waiting(n5)
        n6 = next(gen2)
        assert n6.name == '_regex_target_tgt1:t1'

        # file_dep is removed because foo might not be task
        # that creates this task (support for multi regex matches)
        assert n6.file_dep == {}


    def test_regex_group_already_created(self):
        # this is required to avoid loading more tasks than required, GH-#60
        def creator1():
            yield Task('foo1', None, targets=['tgt1'])
        delayed_loader1 = DelayedLoader(creator1, target_regex='tgt.*')

        def creator2():  # pragma: no cover
            yield Task('foo2', None, targets=['tgt2'])
        delayed_loader2 = DelayedLoader(creator2, target_regex='tgt.*')

        t1 = Task('t1', None, loader=delayed_loader1)
        t2 = Task('t2', None, loader=delayed_loader2)

        tc = TaskControl([t1, t2])
        selection = tc._filter_tasks(['tgt1'])
        assert ['_regex_target_tgt1:t1', '_regex_target_tgt1:t2'] == selection
        td = TaskDispatcher(tc.tasks, tc.targets, selection)

        n1 = td._gen_node(None, '_regex_target_tgt1:t1')
        gen = td._add_task(n1)

        # delayed loader executed, so generator is reset
        n1b = next(gen)
        assert n1b == "reset generator"

        # manually reset generator
        n1.reset_task(td.tasks[n1.task.name], td._add_task(n1))

        # get the delayed created task
        gen1b = n1.generator  # n1 generator was reset / replaced
        # get t1 because of its target was a file_dep of _regex_target_tgt1
        n1c = next(gen1b)
        assert n1c.task.name == 'foo1'

        # get internal created task
        n1c.run_status = 'done'
        td._update_waiting(n1c)
        n1d = next(gen1b)
        assert n1d.name == '_regex_target_tgt1:t1'

        ## go for second selected task
        n2 = td._gen_node(None, '_regex_target_tgt1:t2')
        gen2 = td._add_task(n2)
        # loader is not executed because target t1 was already found
        pytest.raises(StopIteration, next, gen2)


    def test_regex_not_found(self):
        def creator1():
            yield Task('foo1', None, targets=['tgt1'])
        delayed_loader1 = DelayedLoader(creator1, target_regex='tgt.*')

        t1 = Task('t1', None, loader=delayed_loader1)

        tc = TaskControl([t1])
        selection = tc._filter_tasks(['tgt666'])
        assert ['_regex_target_tgt666:t1'] == selection
        td = TaskDispatcher(tc.tasks, tc.targets, selection)

        n1 = td._gen_node(None, '_regex_target_tgt666:t1')
        gen = td._add_task(n1)
        # target not found after generating all tasks from regex group
        pytest.raises(InvalidCommand, next, gen)




class TestTaskDispatcher_get_next_node(object):
    def test_none(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        assert None == td._get_next_node([], [])

    def test_ready(self):
        tasks = {'t1': Task('t1', None),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        ready = deque([n1])
        assert n1 == td._get_next_node(ready, ['t2'])
        assert 0 == len(ready)

    def test_to_run(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        to_run = ['t2', 't1']
        td._gen_node(None, 't1') # t1 was already created
        got = td._get_next_node([], to_run)
        assert isinstance(got, ExecNode)
        assert 't2' == got.task.name
        assert [] == to_run

    def test_to_run_none(self):
        tasks = {'t1': Task('t1', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        td._gen_node(None, 't1') # t1 was already created
        to_run = ['t1']
        assert None == td._get_next_node([], to_run)
        assert [] == to_run


class TestTaskDispatcher_update_waiting(object):
    def test_wait_select(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n2 = td._gen_node(None, 't2')
        n2.wait_select = True
        n2.run_status = 'run'
        td.waiting.add(n2)
        td._update_waiting(n2)
        assert False == n2.wait_select
        assert deque([n2]) == td.ready

    def test_wait_run(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        td._node_add_wait_run(n1, ['t2'])
        n2.run_status = 'done'
        td.waiting.add(n1)
        td._update_waiting(n2)
        assert not n1.bad_deps
        assert deque([n1]) == td.ready
        assert 0 == len(td.waiting)

    def test_wait_run_deps_not_ok(self):
        tasks = {'t1': Task('t1', None, task_dep=['t2']),
                 't2': Task('t2', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n2 = td._gen_node(None, 't2')
        td._node_add_wait_run(n1, ['t2'])
        n2.run_status = 'failure'
        td.waiting.add(n1)
        td._update_waiting(n2)
        assert n1.bad_deps
        assert deque([n1]) == td.ready
        assert 0 == len(td.waiting)

    def test_waiting_node_updated(self):
        tasks = {'t1': Task('t1', None, calc_dep=['t2'], task_dep=['t4']),
                 't2': Task('t2', None),
                 't3': Task('t3', None),
                 't4': Task('t4', None),
                 }
        td = TaskDispatcher(tasks, [], None)
        n1 = td._gen_node(None, 't1')
        n1_gen = td._add_task(n1)
        n2 = next(n1_gen)
        assert 't2' == n2.task.name
        assert 't4' == next(n1_gen).task.name
        assert 'wait' == next(n1_gen)
        assert set() == n1.calc_dep
        assert td.waiting == set()

        n2.run_status = 'done'
        n2.task.values = {'calc_dep': ['t2', 't3'], 'task_dep':['t5']}
        assert n1.calc_dep == set()
        assert n1.task_dep == []
        td._update_waiting(n2)
        assert n1.calc_dep == set(['t3'])
        assert n1.task_dep == ['t5']



class TestTaskDispatcher_dispatcher_generator(object):
    def test_normal(self):
        tasks = [Task("t1", None, task_dep=["t2"]),
                 Task("t2", None,)]
        control = TaskControl(tasks)
        control.process(['t1'])
        gen = control.task_dispatcher().generator
        n2 = next(gen)
        assert tasks[1] == n2.task
        assert "hold on" == next(gen)
        assert "hold on" == next(gen) # hold until t2 is done
        assert tasks[0] == gen.send(n2).task
        pytest.raises(StopIteration, lambda gen: next(gen), gen)


    def test_delayed_creation(self):
        def creator():
            yield {'name': 'foo1', 'actions': None, 'file_dep': ['bar']}
            yield {'name': 'foo2', 'actions': None, 'targets': ['bar']}

        delayed_loader = DelayedLoader(creator, executed='t2')
        tasks = [Task('t0', None, task_dep=['t1']),
                 Task('t1', None, loader=delayed_loader),
                 Task('t2', None)]

        control = TaskControl(tasks)
        control.process(['t0'])
        disp = control.task_dispatcher()
        gen = disp.generator
        nt2 = next(gen)
        assert nt2.task.name == "t2"

        # wait for t2 to be executed
        assert "hold on" == next(gen)
        assert "hold on" == next(gen) # hold until t2 is done

        # delayed creation of tasks for t1 does not mess existing info
        assert disp.nodes['t1'].waiting_me == set([disp.nodes['t0']])
        nf2 = gen.send(nt2)
        assert disp.nodes['t1'].waiting_me == set([disp.nodes['t0']])

        assert nf2.task.name == "t1:foo2"
        nf1 = gen.send(nf2)
        assert nf1.task.name == "t1:foo1"
        assert nf1.task.task_dep == ['t1:foo2'] # implicit dep added
        nt1 = gen.send(nf1)
        assert nt1.task.name == "t1"
        nt0 = gen.send(nt1)
        assert nt0.task.name == "t0"
        pytest.raises(StopIteration, lambda gen: next(gen), gen)
