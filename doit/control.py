"""Control tasks execution order"""
import fnmatch
from collections import deque

from .exceptions import InvalidTask, InvalidCommand, InvalidDodoFile
from .task import Task



class TaskControl(object):
    """Manages tasks inter-relationship

    There are 3 phases
      1) the constructor gets a list of tasks and do initialization
      2) 'process' the command line options for tasks are processed
      3) 'task_dispatcher' dispatch tasks to runner

    Process dependencies and targets to find out the order tasks
    should be executed. Also apply filter to exclude tasks from
    execution. And parse task cmd line options.

    @ivar tasks: (dict) Key: task name ([taskgen.]name)
                               Value: L{Task} instance
    @ivar targets: (dict) Key: fileName
                          Value: task_name
    """

    def __init__(self, task_list):
        self.tasks = {}
        self.targets = {}

        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependecies require so.
        self._def_order = []
        # list of tasks selected to be executed
        self.selected_tasks = None

        # sanity check and create tasks dict
        for task in task_list:
            # task must be a Task
            if not isinstance(task, Task):
                msg = "Task must an instance of Task class. %s"
                raise InvalidTask(msg % (task.__class__))
            # task name must be unique
            if task.name in self.tasks:
                msg = "Task names must be unique. %s"
                raise InvalidDodoFile(msg % task.name)

            self.tasks[task.name] = task
            self._def_order.append(task.name)

        # expand wild-card task-dependencies
        for task in self.tasks.itervalues():
            for pattern in task.wild_dep:
                task.task_dep.extend(self._get_wild_tasks(pattern))

        self._check_dep_names()
        self._init_implicit_deps()


    def _check_dep_names(self):
        """check if user input task_dep or setup_task that doesnt exist"""
        # check task-dependencies exist.
        for task in self.tasks.itervalues():
            for dep in task.task_dep:
                if dep not in self.tasks:
                    msg = "%s. Task dependency '%s' does not exist."
                    raise InvalidTask(msg% (task.name, dep))

            for setup_task in task.setup_tasks:
                if setup_task not in self.tasks:
                    msg = "Task '%s': invalid setup task '%s'."
                    raise InvalidTask(msg % (task.name, setup_task))


    def _init_implicit_deps(self):
        """get task_dep based on file_dep on a target from another task"""
        # 1) create a dictionary associating every target->task. where the task
        # builds that target.
        for task in self.tasks.itervalues():
            for target in task.targets:
                if target in self.targets:
                    msg = ("Two different tasks can't have a common target." +
                           "'%s' is a target for %s and %s.")
                    raise InvalidTask(msg % (target, task.name,
                                             self.targets[target]))
                self.targets[target] = task.name
        # 2) now go through all dependencies and check if they are target from
        # another task.
        for task in self.tasks.itervalues():
            self.add_implicit_task_dep(self.targets, task, task.file_dep)


    @staticmethod
    def add_implicit_task_dep(targets, task, deps_list):
        """add tasks which created targets are file_dep for this task"""
        for dep in deps_list:
            if (dep in targets and targets[dep] not in task.task_dep):
                task.task_dep.append(targets[dep])


    def _get_wild_tasks(self, pattern):
        """get list of tasks that match pattern"""
        wild_list = []
        for t_name in self._def_order:
            if fnmatch.fnmatch(t_name, pattern):
                wild_list.append(t_name)
        return wild_list


    def _process_filter(self, task_selection):
        """process cmd line task options
        [task_name [-task_opt [opt_value]] ...] ...
        """
        filter_list = []
        def add_filtered_task(seq, f_name):
            """can be filter by target or task name """
            filter_list.append(f_name)
            if f_name in self.tasks:
                # parse task_selection
                the_task = self.tasks[f_name]
                # remaining items are other tasks not positional options
                the_task.options, seq = the_task.taskcmd.parse(seq)
            return seq

        # process...
        seq = task_selection[:]
        # process cmd_opts until nothing left
        while seq:
            f_name = seq.pop(0) # always start with a task/target name
            # select tasks by task-name pattern
            if '*' in f_name:
                for task_name in self._get_wild_tasks(f_name):
                    add_filtered_task((), task_name)
            else:
                seq = add_filtered_task(seq, f_name)
        return filter_list


    def _filter_tasks(self, task_selection):
        """Select tasks specified by filter.

        filter can specify tasks to be execute by task name or target.
        @return (list) of string. where elements are task name.
        """
        selected_task = []

        filter_list = self._process_filter(task_selection)
        for filter_ in filter_list:
            # by task name
            if filter_ in self.tasks:
                selected_task.append(filter_)
            # by target
            elif filter_ in self.targets:
                selected_task.append(self.targets[filter_])
            else:
                msg = ('"%s" must be a sub-command, a task, or a target.\n' +
                       'Type "doit help" to see available sub-commands.\n' +
                       'Type "doit list" to see available tasks')
                raise InvalidCommand(msg % filter_)
        return selected_task


    def process(self, task_selection):
        """@return (list - string) each element is the name of a task"""
        # execute only tasks in the filter in the order specified by filter
        if task_selection is not None:
            self.selected_tasks = self._filter_tasks(task_selection)
        else:
            # if no filter is defined execute all tasks
            # in the order they were defined.
            self.selected_tasks = self._def_order


    def task_dispatcher(self, include_setup=False):
        """return a TaskDispatcher generator
        """
        assert self.selected_tasks is not None, \
            "must call 'process' before this"

        disp = TaskDispatcher(self.tasks, self.targets, include_setup)
        return disp.dispatcher_generator(self.selected_tasks)



class ExecNode(object):
    """Each task will have an instace of this
    This used to keep track of waiting events and the generator for dep nodes
    """
    def __init__(self, task, parent):
        self.task = task
        self.ancestors = []
        if parent:
            self.ancestors.extend(parent.ancestors)
        self.ancestors.append(task.name)

        # Wait for a task to finish its execution
        self.wait_run = set() # task names
        self.waiting_me = set() # ExecNode
        # Wait for a task to be selected to its execution
        # checking if it is up-to-date
        self.wait_select = False
        self.generator = None

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.task.name)

    def step(self):
        """get node's next step"""
        try:
            return self.generator.next()
        except StopIteration:
            return None


def no_none(decorated):
    """decorator for a generator to discard/filter-out None values"""
    def _func(*args, **kwargs):
        """wrap generator"""
        for value in decorated(*args, **kwargs):
            if value is not None:
                yield value
    return _func


# FIXME handle task.run_status = 'ignore'
class TaskDispatcher(object):
    """Dispatch another task to be selected/executed, mostly handle with MP

    Note that a dispatched task might not be ready to be executed.
    """
    def __init__(self, tasks, targets, include_setup=False):
        self.tasks = tasks
        self.targets = targets
        self.include_setup = include_setup

        self.nodes = {} # key task-name, value: ExecNode


    def _gen_node(self, parent, task_name):
        """return ExecNode for task_name if not created yet"""
        node = self.nodes.get(task_name, None)

        # first time, create node
        if node is None:
            node = ExecNode(self.tasks[task_name], parent)
            node.generator = self._add_task(node)
            self.nodes[task_name] = node
            return node

        # detect cyclic/recursive dependencies
        if parent and task_name in parent.ancestors:
            msg = "Cyclic/recursive dependencies for task %s: [%s]"
            cycle = " -> ".join(parent.ancestors + [task_name])
            raise InvalidDodoFile(msg % (task_name, cycle))


    def _node_add_wait_run(self, node, task_list):
        """updates node.wait_run and returns value for _add_task generator"""
        wait_for = set(n for n in task_list if self.tasks[n].run_status not in (
                'done', 'up-to-date'))
        for name in wait_for:
            self.nodes[name].waiting_me.add(node)
        node.wait_run.update(wait_for)
        return 'wait' if node.wait_run else None


    @no_none
    def _add_task(self, node):
        """@return a generator that produces:
             - ExecNode for task dependencies
             - 'wait' to wait for an event (i.e. a dep task run)
             - Task when ready to run (or be selected)
             - None values are of no interest and are filtered out
               by the decorator no_none

        note that after a 'wait' is sent it is the reponsability of the
        caller to ensure the current ExecNode cleared all its waiting
        before calling `next()` again on this generator
        """
        this_task = node.task

        # add calc_dep
        # FIXME calc_dep  cant run in parallel
        while this_task.calc_dep_stack:
            # get next dynamic task
            dyn = self.tasks[this_task.calc_dep_stack.pop(0)]
            yield self._gen_node(node, dyn.name)
            yield self._node_add_wait_run(node, (dyn.name,))
            # refresh this task dependencies
            this_task.update_deps(dyn.values)
            TaskControl.add_implicit_task_dep(self.targets, this_task,
                                              dyn.values.get('file_dep', []))

        # add task_dep
        for task_dep in this_task.task_dep:
            yield self._gen_node(node, task_dep)
        yield self._node_add_wait_run(node, this_task.task_dep)

        # add itself
        yield this_task

        # tasks that contain setup-tasks need to be yielded twice
        if this_task.setup_tasks:
            # run_status None means task is waiting for other tasks
            # in order to check if up-to-date. so it needs to wait
            # before scheduling its setup-tasks.
            if this_task.run_status is None:
                node.wait_select = True
                yield "wait"

            # this task should run, so schedule setup-tasks before itself
            if this_task.run_status == 'run' or self.include_setup:
                for setup_task in this_task.setup_tasks:
                    yield self._gen_node(node, setup_task)
                yield self._node_add_wait_run(node, this_task.setup_tasks)

                # re-send this task after setup_tasks are sent
                yield this_task


    def _get_next_node(self, ready, tasks_to_run):
        """get node/task from (in order):
            .1 ready
            .2 to_run
         """
        if ready:
            return ready.popleft()

        # get task group from tasks_to_run
        while tasks_to_run:
            task_name = tasks_to_run.pop()
            node = self._gen_node(None, task_name)
            if node:
                return node

    def _update_waiting(self, processed, ready, waiting):
        """updates 'ready' and 'waiting' queues after processed
        @param processed (Task) or None
        """
        # no task processed, just ignore
        if processed is None:
            return

        node = self.nodes[processed.name]

        # if node was waiting select must only receive select event
        if node.wait_select:
            ready.append(node)
            node.wait_select = False

        # status != run means this was not just select completed
        if node.task.run_status in ('done', 'up-to-date'):
            for waiting_node in node.waiting_me:
                waiting_node.wait_run.remove(node.task.name)
                if not waiting_node.wait_run:
                    ready.append(waiting_node)
                    waiting.remove(waiting_node)
        else:
            assert node.task.run_status == 'run'



    def dispatcher_generator(self, selected_tasks):
        """return generator dispatching tasks"""
        # each selected task will create a tree (from dependencies) of
        # tasks to be processed
        tasks_to_run = list(reversed(selected_tasks))
        waiting = set() # of ExecNode
        ready = deque() # of ExecNode
        node = None  # current active ExecNode

        while True:
            # get current node
            if not node:
                node = self._get_next_node(ready, tasks_to_run)
                if not node:
                    if waiting:
                        # all tasks are waiting, hold on
                        processed = (yield "hold on")
                        self._update_waiting(processed, ready, waiting)
                        continue
                    # we are done!
                    return

            # get next step from current node
            next_step = node.step()

            # got None, nothing left for this generator
            if next_step is None:
                node = None
                continue

            # got a task, send task to runner
            if isinstance(next_step, Task):
                processed = (yield next_step)
                self._update_waiting(processed, ready, waiting)

            # got new ExecNode, add to ready_queue
            elif isinstance(next_step, ExecNode):
                ready.append(next_step)

            # got 'wait', add ExecNode to waiting queue
            else:
                assert next_step == "wait"
                # skip all waiting tasks, just getting a list of tasks...
                if not self.include_setup:
                    waiting.add(node)
                    node = None

