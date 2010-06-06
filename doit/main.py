"""Loads dodo file (a python module) and `doit` command line programs"""
import os
import sys
import inspect
import types
import fnmatch

from doit.task import InvalidTask, Task, dict_to_task

class InvalidCommand(Exception):
    """Invalid command line argument."""
    pass

class InvalidDodoFile(Exception):
    """Invalid dodo file"""
    pass

# TASK_STRING: (string) prefix used to identify python function
# that are task generators in a dodo file.
TASK_STRING = "task_"


def isgenerator(object):
    """Check if object type is a generator.

    @param object: object to test.
    @return: (bool) object is a generator?"""
    return type(object) is types.GeneratorType


def get_module(dodoFile, cwd=None):
    """
    @param dodoFile(str): path to file containing the tasks
    @param cwd(str): path to be used cwd, if None use path from dodoFile
    @return (module) dodo module
    """
    ## load module dodo file and set environment
    base_path, file_name = os.path.split(os.path.abspath(dodoFile))
    # make sure dodo path is on sys.path so we can import it
    sys.path.insert(0, base_path)

    if cwd is None:
        # by default cwd is same as dodo.py base path
        full_cwd = base_path
    else:
        # insert specified cwd into sys.path
        full_cwd = os.path.abspath(cwd)
        if not os.path.isdir(full_cwd):
            msg = "Specified 'dir' path must be a directory.\nGot '%s'(%s)."
            raise InvalidCommand(msg % (cwd, full_cwd))
        sys.path.insert(0, full_cwd)

    if not os.path.exists(dodoFile):
        msg = ("Could not find dodo file '%s'.\n" +
               "Please use '-f' to specify file name.\n")
        raise InvalidDodoFile(msg % dodoFile)

    # file specified on dodo file are relative to cwd
    os.chdir(full_cwd)

    # get module containing the tasks
    return __import__(os.path.splitext(file_name)[0])


def load_task_generators(dodo_module, command_names=()):
    """Loads a python file and extracts its task generator functions.

    The python file is a called "dodo" file.

    @param dodo_module: (module) module containing the tasks
    @param command_names: (list - str) blacklist for task names
    @return (dict):
     - task_list (list) of Tasks in the order they were defined on the file
     - default_tasks (list) of tasks to be executed by default
    """

    # get functions defined in the module and select the task generators
    # a task generator function name starts with the string TASK_STRING
    funcs = []
    prefix_len = len(TASK_STRING)
    # get all functions defined in the module
    for name, ref in inspect.getmembers(dodo_module, inspect.isfunction):
        # ignore functions that are not a task (by its name)
        if not name.startswith(TASK_STRING):
            continue
        # remove TASK_STRING prefix from name
        task_name = name[prefix_len:]
        # tasks cant have name of commands
        if task_name in command_names:
            msg = ("Task can't be called '%s' because this is a command name."+
                   " Please choose another name.")
            raise InvalidDodoFile(msg % task_name)
        # get line number where function is defined
        line = inspect.getsourcelines(ref)[1]
        # add to list task generator functions
        funcs.append((task_name, ref, line))

    # sort by the order functions were defined (line number)
    funcs.sort(key=lambda obj:obj[2])

    # generate all tasks
    task_list = []
    for name, ref, line in funcs:
        task_list.extend(generate_tasks(name, ref(), ref.__doc__))

    doit_config = getattr(dodo_module, 'DOIT_CONFIG', {})
    if not isinstance(doit_config, dict):
        msg = ("DOIT_CONFIG  must be a dict. got:'%s'%s")
        raise InvalidDodoFile(msg % (repr(doit_config),type(doit_config)))

    return {'task_list': task_list,
            'config': doit_config}

def generate_tasks(name, gen_result, gen_doc=None):
    """Create tasks from a task generator result.

    @param name: (string) name of taskgen function
    @param gen_result: value returned by a task generator function
    @param gen_doc: (string/None) docstring from the task generator function
    @return: (tuple) task,list of subtasks
    """
    # task described as a dictionary
    if isinstance(gen_result,dict):
        if 'name' in gen_result:
            raise InvalidTask("Task %s. Only subtasks use field name."%name)

        gen_result['name'] = name

        # Use task generator docstring
        # if no doc present in task dict
        if not 'doc' in gen_result:
            gen_result['doc'] = gen_doc

        return [dict_to_task(gen_result)]

    # a generator
    if isgenerator(gen_result):
        group_task = Task(name, None, doc=gen_doc)
        tasks = [group_task]
        # the generator return subtasks as dictionaries .
        for task_dict in gen_result:
            # check valid input
            if not isinstance(task_dict, dict):
                raise InvalidTask("Task %s must yield dictionaries"% name)

            if 'name' not in task_dict:
                raise InvalidTask("Task %s must contain field name. %s"%
                                  (name,task_dict))
            # name is task.subtask
            task_dict['name'] = "%s:%s"% (name,task_dict.get('name'))
            sub_task = dict_to_task(task_dict)
            sub_task.is_subtask = True
            tasks.append(sub_task)

        # add task dependencies to group task.
        group_task.task_dep = [task.name for task in tasks[1:]]
        return tasks

    raise InvalidTask("Task %s. Must return a dictionary. got %s" %
                      (name, type(gen_result)))


def get_tasks(dodo_file, cwd, command_names):
    """get tasks from dodo_file"""
    dodo_module = get_module(dodo_file, cwd)
    return load_task_generators(dodo_module, command_names)



class WaitTask(object):
    def __init__(self, task_name):
        self.task_name = task_name

class WaitSelectTask(WaitTask):
    def ready(self, status):
        return status is not None

class WaitRunTask(WaitTask):
    def ready(self, status):
        return status in ('done', 'up-to-date')

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

    def __init__(self, task_list):
        self.tasks = {}
        self.targets = {}

        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependecies require so.
        self._def_order = []
        # list of tasks selected to be executed
        self.selected_tasks = None

        # FIXME doc
        self._add_status = {} # key task-name, value: generato_id

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
                    raise InvalidTask(msg% (task.name,dep))

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
                    self.targets[dep] not in task.task_dep):
                    task.task_dep.append(self.targets[dep].name)


    def _get_wild_tasks(self, pattern):
        """get list of tasks that match pattern"""
        wild_list = []
        for t_name in self._def_order:
            if fnmatch.fnmatch(t_name, pattern):
                wild_list.append(t_name)
        return wild_list


    def _process_filter(self, task_selection):
        # process cmd line task options
        # [task_name [-task_opt [opt_value]] ...] ...
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
        selectedTask = []

        filter_list = self._process_filter(task_selection)
        for filter_ in filter_list:
            # by task name
            if filter_ in self.tasks:
                selectedTask.append(filter_)
            # by target
            elif filter_ in self.targets:
                selectedTask.append(self.targets[filter_].name)
            else:
                msg = ('"%s" must be a sub-command, a task, or a target.\n' +
                       'Type "doit help" to see available sub-commands.\n' +
                       'Type "doit list" to see available tasks')
                raise InvalidCommand(msg % filter_)
        return selectedTask


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
        # used in the place of gen_id to indicate task was "completely"  added
        ADDED = -1

        # check if this was already added
        if task_name in self._add_status:
            # check task was alaready added, nothing to do. stop iteration
            if self._add_status[task_name] == ADDED:
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

        # execute dynamic tasks
        while this_task.calc_dep_stack:
            # get next dynamic task
            dyn = self.tasks[this_task.calc_dep_stack.pop(0)]
            # add dependencies from dynamic task
            for tk in self._add_task(gen_id, dyn.name, include_setup):
                yield tk
            # wait for dynamic task to complete
            yield WaitRunTask(dyn.name)
            # refresh this task dependencies
            if 'dd' in dyn.values:
                this_task._init_dependencies(dyn.values['dd'])

        # add dependencies first
        for dependency in this_task.task_dep:
            for tk in self._add_task(gen_id, dependency, include_setup):
                yield tk

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
                for st in this_task.setup_tasks:
                    # TODO check st is a valid task name
                    for tk in self._add_task(gen_id, st, include_setup):
                        yield tk
                # re-send this task after setup_tasks are sent
                yield self.tasks[task_name]

        # done with this task
        self._add_status[task_name] = ADDED


    def task_dispatcher(self, include_setup=False):
        """Dispatch another task to be executed, mostly handle with MP

        Note that a dispatched task might not be ready to be executed.
        """
        assert self.selected_tasks is not None, "must call 'process' before this"

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
                for wt, wait in task_gens.iteritems():
                    if wait.ready(self.tasks[wt].run_status):
                        current_gen = task_gens[wt].task_gen
                        del task_gens[wt]
                        break

            # get task group from tasks_to_run
            if not current_gen:
                # all task are waiting, hold on
                if not tasks_to_run:
                    yield "hold on"
                    continue
                task_name = tasks_to_run.pop(0)
                # seed task generator
                current_gen = self._add_task(gen_id, task_name, include_setup)
                gen_id += 1

            # get next task from current generator
            try:
                next = current_gen.next()
            except StopIteration:
                # nothing left for this generator
                current_gen = None
                continue

            # str means this generator is on hold, add to waiting dict
            if isinstance(next, WaitTask):
                if next not in task_gens:
                    next.task_gen = current_gen
                    task_gens[next.task_name] = next
                current_gen = None
            # get task from current group
            else:
                assert isinstance(next,Task), next
                yield next

