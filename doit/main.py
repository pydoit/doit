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

    # DEPRECATION on doit 0.7 - TODO remove this on doit 0.8
    # get default tasks
    if getattr(dodo_module, 'DEFAULT_TASKS', None):
        msg = ("DEFAULT_TASKS usage is deprecated. Please use DOIT_CONFIG = {" +
               "'default_tasks': [<task_list>]}")
        sys.stderr.write("DEPRECATION WARNING: %s\n" % msg)
        doit_config['default_tasks'] = dodo_module.DEFAULT_TASKS

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


# this name is confusing with task.setup which it doesnt have any relation...
class TaskSetup(object):
    """
    Process dependencies and targets to find out the order tasks
    should be executed. Also apply filter to exclude tasks from
    execution. And parse task cmd line options.

    @ivar filter: (sequence of strings) selection of tasks to execute
                                        (task/target names)
    @ivar tasks: (dict) Key: task name ([taskgen.]name)
                               Value: L{Task} instance
    @ivar targets: (dict) Key: fileName
                          Value: L{Task} instance
    """

    def __init__(self, task_list):

        self.targets = {}
        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependecies require so.
        self.task_order = []
        # dict of tasks by name
        self.tasks = {}

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
            self.task_order.append(task.name)

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
                for t_name in self.task_order:
                    task = self.tasks[t_name]
                    if fnmatch.fnmatch(task.name, f_name):
                        add_filtered_task((), task.name)
            else:
                seq = add_filtered_task(seq, f_name)
        return filter_list


    def filter_tasks(self, task_selection):
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

    def _order_tasks(self, to_add):
        """put tasks in an order so that dependencies are executed before.
        make sure a task is added only once. detected cyclic dependencies.
        """
        ADDING, ADDED = 0, 1
        status = {}
        task_in_order = []

        def add_task(task_name):
            if task_name in status:
                # check task was alaready added
                if status[task_name] == ADDED:
                    return

                # detect cyclic/recursive dependencies
                if status[task_name] == ADDING:
                    msg = "Cyclic/recursive dependencies for task %s"
                    raise InvalidDodoFile(msg % task_name)

            status[task_name] = ADDING

            # add dependencies first
            for dependency in self.tasks[task_name].task_dep:
                add_task(dependency)

            # add itself
            task_in_order.append(self.tasks[task_name])
            status[task_name] = ADDED

        for name in to_add:
            add_task(name)
        return task_in_order


    def process(self, task_selection):
        """@return (list - string) each element is the name of a task"""
        # if no filter is defined execute all tasks
        # in the order they were defined.
        selectedTask = self.task_order
        # execute only tasks in the filter in the order specified by filter
        if task_selection is not None:
            selectedTask = self.filter_tasks(task_selection)
        return self._order_tasks(selectedTask)
