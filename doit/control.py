"""Control tasks execution order"""
import fnmatch

from .exceptions import InvalidTask, InvalidCommand, InvalidDodoFile
from .task import Task


class WaitTask(object):
    """Keep reference for waiting for a task"""
    def __init__(self, task_name):
        self.task_name = task_name

class WaitSelectTask(WaitTask):
    """Wait for a task to be selected to its execution
    (checking if it is up-to-date)
    """
    @staticmethod
    def ready(status):
        """check if task is ready, no loger need to wait
        For a "select" wait a task has any status
        """
        return status is not None

class WaitRunTask(WaitTask):
    """Wait for a task to finish its execution"""
    READY_STATUS = ('done', 'up-to-date')

    @classmethod
    def ready(cls, status):
        """check if task is ready, no loger need to wait
        For a running task needs to wait for its completion
        """
        return status in cls.READY_STATUS


class TaskControl(object):
    """Manages tasks inter-relationship

    There are 3 phases
      1) the constructor gets a list of tasks and do initialization
      2) 'process' the command line options for tasks are processed
      3) 'get_next_task' dispatch tasks to runner

    Process dependencies and targets to find out the order tasks
    should be executed. Also apply filter to exclude tasks from
    execution. And parse task cmd line options.

    @ivar tasks: (dict) Key: task name ([taskgen.]name)
                               Value: L{Task} instance
    @ivar targets: (dict) Key: fileName
                          Value: L{Task} instance
    """

    # indicate task already finish being handled by a generator from
    # the dispatcher
    DONE = -1

    def __init__(self, task_list):
        self.tasks = {}
        self.targets = {}

        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependecies require so.
        self._def_order = []
        # list of tasks selected to be executed
        self.selected_tasks = None

        # indicate which generator is handling this task or DONE
        self._add_status = {} # key task-name, value: generator_id

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

        # check task-dependencies exist.
        for task in self.tasks.itervalues():
            for dep in task.task_dep:
                if dep not in self.tasks:
                    msg = "%s. Task dependency '%s' does not exist."
                    raise InvalidTask(msg% (task.name, dep))

        # get target dependecies on other tasks based on file dependency on
        # a target.
        # 1) create a dictionary associating every target->task. where the task
        # builds that target.
        for task in self.tasks.itervalues():
            for target in task.targets:
                if target in self.targets:
                    msg = ("Two different tasks can't have a common target." +
                           "'%s' is a target for %s and %s.")
                    raise InvalidTask(msg % (target, task.name,
                                             self.targets[target].name))
                self.targets[target] = task
        # 2) now go through all dependencies and check if they are target from
        # another task.
        for task in self.tasks.itervalues():
            for dep in task.file_dep:
                if (dep in self.targets and
                    self.targets[dep].name not in task.task_dep):
                    task.task_dep.append(self.targets[dep].name)


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
                selected_task.append(self.targets[filter_].name)
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


    def _add_task(self, gen_id, task_name, include_setup):
        """generator of tasks to be executed
        @return Task if ready. or task's name that should be put on hold
        """

        # check if this was already added
        if task_name in self._add_status:
            # check task was alaready added, nothing to do. stop iteration
            if self._add_status[task_name] == self.DONE:
                return
            # detect cyclic/recursive dependencies
            if self._add_status[task_name] == gen_id:
                msg = "Cyclic/recursive dependencies for task %s"
                raise InvalidDodoFile(msg % task_name)
            # is running on another generator
            if self._add_status[task_name] != gen_id:
                return

        self._add_status[task_name] = gen_id
        this_task = self.tasks[task_name]

        # execute dynamic calculated dep tasks
        while this_task.calc_dep_stack:
            # get next dynamic task
            dyn = self.tasks[this_task.calc_dep_stack.pop(0)]
            # add dependencies from dynamic task
            for dyn_task in self._add_task(gen_id, dyn.name, include_setup):
                yield dyn_task
            # wait for dynamic task to complete
            if not include_setup:
                yield WaitRunTask(dyn.name)
            # refresh this task dependencies
            this_task.update_deps(dyn.values)

        # add dependencies first
        for dependency in this_task.task_dep:
            for dep_task in self._add_task(gen_id, dependency, include_setup):
                yield dep_task

        # add itself
        yield self.tasks[task_name]

        # tasks that contain setup-tasks need to be yielded twice
        if this_task.setup_tasks:
            # run_status None means task is waiting for other tasks
            # in order to check if up-to-date. so it needs to wait
            # before scheduling its setup-tasks.
            if this_task.run_status is None and not include_setup:
                yield WaitSelectTask(task_name)

            # this task should run, so schedule setup-tasks before itself
            if this_task.run_status == 'run' or include_setup:
                for setup_task in this_task.setup_tasks:
                    if setup_task not in self.tasks:
                        msg = "Task '%s': invalid setup task '%s'."
                        raise InvalidTask(msg % (this_task.name, setup_task))
                    for setup_dep in self._add_task(gen_id, setup_task,
                                                    include_setup):
                        yield setup_dep
                # re-send this task after setup_tasks are sent
                yield self.tasks[task_name]

        # done with this task
        self._add_status[task_name] = self.DONE


    def task_dispatcher(self, include_setup=False):
        """Dispatch another task to be executed, mostly handle with MP

        Note that a dispatched task might not be ready to be executed.
        """
        assert self.selected_tasks is not None, \
            "must call 'process' before this"

        # each selected task will create a tree (from dependencies) of
        # tasks to be processed
        tasks_to_run = self.selected_tasks[:]
        # waiting task generators
        # key (str): name of the task to wait for
        # value (list): add_task generator waiting for this task
        task_gens = {}
        # current active task generator
        current_gen = None
        gen_id = 1
        while tasks_to_run or task_gens or current_gen:
            ## get task from (in order):
            # 1 - current task generator
            # 2 - waiting task generator
            # 3 - to_run list

            # get task group from waiting queue
            if not current_gen:
                for wait_name, wait in task_gens.iteritems():
                    if wait.ready(self.tasks[wait_name].run_status):
                        current_gen = task_gens[wait_name].task_gen
                        del task_gens[wait_name]
                        break

            # get task group from tasks_to_run
            if not current_gen:
                # all tasks are waiting, hold on
                if not tasks_to_run:
                    yield "hold on"
                    continue
                task_name = tasks_to_run.pop(0)
                # seed task generator
                current_gen = self._add_task(gen_id, task_name, include_setup)
                gen_id += 1

            # get next task from current generator
            try:
                next_task = current_gen.next()
            except StopIteration:
                # nothing left for this generator
                current_gen = None
                continue

            # str means this generator is on hold, add to waiting dict
            if isinstance(next_task, WaitTask):
                if next_task not in task_gens:
                    next_task.task_gen = current_gen
                    task_gens[next_task.task_name] = next_task
                current_gen = None
            # get task from current group
            else:
                assert isinstance(next_task, Task), next_task
                yield next_task

