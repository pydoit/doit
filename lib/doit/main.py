import os
import sys
import inspect

from doit.util import isgenerator
from doit.task import InvalidTask, BaseTask, GroupTask, dict_to_task
from doit import runner

class InvalidCommand(Exception):
    """Invalid command line argument."""
    pass

class InvalidDodoFile(Exception):
    """Invalid dodo file"""
    pass

# TASK_STRING: (string) prefix used to identify python function
# that are task generators in a dodo file.
TASK_STRING = "task_"

def get_module(dodoFile):
    """
    @param dodoFile: (string) path to file containing the tasks
    @return (module) dodo module
    """
    ## load module dodo file and set environment
    base_path, file_name = os.path.split(os.path.abspath(dodoFile))
    # make sure dir is on sys.path so we can import it
    sys.path.insert(0, base_path)
    # file specified on dodo file are relative to itself.
    os.chdir(base_path)
    # get module containing the tasks
    return __import__(os.path.splitext(file_name)[0])

def load_task_generators(dodo_module):
    """Loads a python file and extracts its task generator functions.

    The python file is a called "dodo" file.

    @param dodo_module: (module) module containing the tasks
    @return (dict):
     - task_list (list) of BaseTasks in the order they were defined on the file
     - default_tasks (list) of tasks to be executed by default
    """

    # get functions defined in the module and select the task generators
    # a task generator function name starts with the string TASK_STRING
    funcs = []
    prefix_len = len(TASK_STRING)
    # get all functions defined in the module
    for name,ref in inspect.getmembers(dodo_module, inspect.isfunction):
        # ignore functions that are not a task (by its name)
        if not name.startswith(TASK_STRING):
            continue
        # get line number where function is defined
        line = inspect.getsourcelines(ref)[1]
        # add to list task generator functions
        # remove TASK_STRING prefix from name
        funcs.append((name[prefix_len:],ref,line))

    # sort by the order functions were defined (line number)
    funcs.sort(key=lambda obj:obj[2])

    # generate all tasks
    task_list = []
    for name, ref, line in funcs:
        task_list.extend(generate_tasks(name, ref()))

    # get default tasks
    default_tasks = getattr(dodo_module, 'DEFAULT_TASKS', None)
    if default_tasks is not None and (not isinstance(default_tasks, list)):
        msg = ("DEFAULT_TASKS  paramater 'dependencies' must be a list." +
               "got:'%s'%s")
        raise InvalidDodoFile(msg % (str(default_tasks),type(default_tasks)))

    return {'task_list': task_list,
            'default_tasks': default_tasks}

def generate_tasks(name, gen_result):
    """Create tasks from a task generator result.

    @param name: (string) name of taskgen function
    @param gen_result: value returned by a task generator function
    @return: (tuple) task,list of subtasks
    """
    # task described as a dictionary
    if isinstance(gen_result,dict):
        if 'name' in gen_result:
            raise InvalidTask("Task %s. Only subtasks use field name."%name)

        gen_result['name'] = name
        return [dict_to_task(gen_result)]

    # a generator
    if isgenerator(gen_result):
        group_task = GroupTask(name, None)
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
            sub_task.isSubtask = True
            tasks.append(sub_task)

        # add task dependencies to group task.
        group_task.task_dep = [task.name for task in tasks[1:]]
        return tasks

    # if not a dictionary nor a generator. "task" is the action itself.
    return [dict_to_task({'name':name,'action':gen_result})]



class TaskSetup(object):
    """
    Process dependencies and targets to find out the order tasks
    should be executed. Also apply filter to exclude tasks from
    execution.

    @ivar filter: (sequence of strings) selection of tasks to execute
    @ivar tasks: (dict) Key: task name ([taskgen.]name)
                               Value: L{BaseTask} instance
    @ivar targets: (dict) Key: fileName
                          Value: L{BaseTask} instance
    """

    def __init__(self, task_list, filter_=None):

        self.filter = filter_
        self.targets = {}
        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependecies require so.
        self.task_order = []
        # dict of tasks by name
        self.tasks = {}

        # sanity check and create tasks dict
        for task in task_list:
            # task must be a BaseTask
            if not isinstance(task, BaseTask):
                msg = "Task must an instance of BaseTask class. %s"
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
                # TODO support more than one task with same target or raise
                # an error
                self.targets[target] = task
        # 2) now go through all dependencies and check if they are target from
        # another task.
        for task in self.tasks.itervalues():
            for dep in task.file_dep:
                if (dep in self.targets and
                    self.targets[dep] not in task.task_dep):
                    task.task_dep.append(self.targets[dep].name)


    def _filter_tasks(self):
        """Select tasks specified by filter.

        filter can specify tasks to be execute by task name or target.
        @return (list) of string. where elements are task name.
        """
        selectedTask = []
        for filter_ in self.filter:
            # by task name
            if filter_ in self.tasks:
                selectedTask.append(filter_)
            # by target
            elif filter_ in self.targets:
                selectedTask.append(self.targets[filter_].name)
            else:
                print self.targets
                raise InvalidCommand('"%s" is not a task/target.'% filter_)
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
                    raise InvalidDodoFile(msg % self.tasks[task_name])

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


    def process(self):
        """@return (list - string) each element is the name of a task"""
        # if no filter is defined execute all tasks
        # in the order they were defined.
        selectedTask = self.task_order
        # execute only tasks in the filter in the order specified by filter
        if self.filter is not None:
            selectedTask = self._filter_tasks()
        return self._order_tasks(selectedTask)



##################################

def doit_run(dependencyFile, task_list, filter_=None, verbosity=0,
            alwaysExecute=False):
    selected_tasks = TaskSetup(task_list, filter_).process()
    return runner.run_tasks(dependencyFile, selected_tasks,
                            verbosity, alwaysExecute)



def doit_list(task_list, printSubtasks):
    """List task generators, in the order they were defined.

    @param printSubtasks: (bool) print subtasks
    """
    print "==== Tasks ===="
    for task in task_list:
        if (not task.isSubtask) or printSubtasks:
            print task.name
    print "="*25,"\n"
    return 0


