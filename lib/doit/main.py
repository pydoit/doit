"""doit command line program."""

import os
import sys
import inspect

from doit.util import isgenerator, OrderedDict
from doit.task import InvalidTask, create_task
from doit.runner import Runner


class InvalidCommand(Exception):
    """Invalid command line argument."""
    pass

class InvalidDodoFile(Exception):
    """Invalid dodo file"""
    pass


# TASK_STRING: (string) prefix used to identify python function
# that are task generators in a dodo file.
TASK_STRING = "task_"

def load_task_generators(dodoFile):
    """Loads a python file and extracts its task generator functions.

    The python file is a called "dodo" file.

    @param dodoFile: (string) path to file containing the tasks
    @return (tupple) (name, function reference)
    """
    ## load module dodo file and set environment
    base_path, file_name = os.path.split(os.path.abspath(dodoFile))
    # make sure dir is on sys.path so we can import it
    sys.path.insert(0, base_path)
    # file specified on dodo file are relative to itself.
    os.chdir(base_path)
    # get module containing the tasks
    dodo_module = __import__(os.path.splitext(file_name)[0])

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
    return [(name,ref) for name,ref,line in funcs]


def _dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict: (dict) task representation as a dict.
    @raise L{InvalidTask}:
    """
    # FIXME: check this in another place
    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in DoitTask.TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))

    # check required fields
    if 'action' not in task_dict:
        raise InvalidTask("Task %s must contain field action. %s"%
                          (task_dict['name'],task_dict))

    return create_task(task_dict.get('name'),
                       task_dict.get('action'),
                       task_dict.get('dependencies',[]),
                       task_dict.get('targets',[]),
                       args=task_dict.get('args',[]),
                       kwargs=task_dict.get('kwargs',{}))


def generate_tasks(name, gen_result):
    """Create tasks from a task generator.

    @param name: (string) name of taskgen function
    @param gen_result: value returned by a task generator function
    @return: (tuple) task,list of subtasks
    """
    # task described as a dictionary
    if isinstance(gen_result,dict):
        if 'name' in gen_result:
            raise InvalidTask("Task %s. Only subtasks use field name."%name)

        gen_result['name'] = name
        return _dict_to_task(gen_result),[]

    # a generator
    if isgenerator(gen_result):
        tasks = []
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
            tasks.append(_dict_to_task(task_dict))
        # TODO return a group-task instead of None?
        return None, tasks

    # if not a dictionary nor a generator. "task" is the action itself.
    return _dict_to_task({'name':name,'action':gen_result}),[]



class DoitTask(object):
    """
    DoitTask contains a task to be executed and keeps information on
    dependencies between tasks. Python-task, and cmd-task do not keep
    information on its relation to other tasks.

    @cvar TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    @cvar UNUSED: task not used.
    @cvar ADDING: adding dependencies (used to detect cyclic dependency).
    @cvar ADDED: task already added to runner.

    @ivar dependsOn: (list of DoitTask) note that dependencies here are tasks
    only, not files as in BaseTask.
    @ivar task: (L{BaseTask}) the task instance used by the L{Runner}.
    @ivar status: (int) one of UNUSED, ADDING, ADDED
    """

    TASK_ATTRS = ('name','action','dependencies','targets','args','kwargs')

    UNUSED = 0
    ADDING = 1
    ADDED = 2


    def __init__(self, task, dependsOn):
        """Init.

        @param task: (L{BaseTask})
        @param dependsOn: list of other L{DoitTask}
        """
        self.task = task
        self.dependsOn = dependsOn
        self.status = self.UNUSED

    def __str__(self):
        if self.task:
            return self.task.name

    # FIXME remove all this callback shit. just get a list and return a list.
    def add_to(self,add_cb):
        """Add task to runner.

        make sure a task is added only once. detected cyclic dependencies.

        @parameter add_cb: (callable/callback) callable must receive one
        parameter (the task). the callebale
        """
        # check task was alaready added
        if self.status == self.ADDED:
            return

        # detect cyclic/recursive dependencies
        if self.status == self.ADDING:
            raise InvalidDodoFile("Cyclic/recursive dependencies for task %s"%\
                                  self)
        self.status = self.ADDING

        # add dependencies first
        for dependency in self.dependsOn:
            dependency.add_to(add_cb)

        # add itself
        if self.task:
            add_cb(self.task)

        self.status = self.ADDED




class Main(object):
    """doit - load dodo file and execute tasks.

    @ivar dependencyFile: (string) file path of the dbm file.
    @ivar verbosity: (bool) verbosity level. @see L{Runner}

    @ivar list: (int) 0 dont list, run;
                      1 list task generators (do not run if listing);
                      2 list all tasks (do not run if listing);
    @ivar filter: (sequence of strings) selection of tasks to execute

    @ivar taskgen: (tupple) (name, function reference)

    @ivar tasks: (OrderedDict) Key: task name ([taskgen.]name)
                               Value: L{DoitTask} instance
    @ivar targets: (dict) Key: fileName
                          Value: L{DoitTask} instance
    """

    def __init__(self, dodoFile, dependencyFile,
                 list_=False, verbosity=0, alwaysExecute=False, filter_=None):

        ## intialize cmd line options
        self.dependencyFile = dependencyFile
        self.list = list_
        self.verbosity = verbosity
        self.alwaysExecute = alwaysExecute
        self.filter = filter_
        self.targets = {}
        self.taskgen = load_task_generators(dodoFile)

        ## get tasks
        self.tasks = OrderedDict()
        # for each task generator
        for name, ref in self.taskgen:
            task, subtasks = generate_tasks(name, ref())
            subDoit = []
            # create subtasks first
            for sub in subtasks:
                doitTask = DoitTask(sub,[])
                self.tasks[sub.name] = doitTask
                subDoit.append(doitTask)
            # create task. depends on subtasks
            self.tasks[name] = DoitTask(task,subDoit)


    def _list_tasks(self, printSubtasks):
        """List task generators, in the order they were defined.

        @param printSubtasks: (bool) print subtasks
        """
        # this function is called when after the constructor,
        # and before task-dependencies and targets are processed
        # so dependsOn contains only subtaks
        print "==== Tasks ===="
        for items in self.taskgen:
            generator = items[0]
            print generator
            if printSubtasks:
                for subtask in self.tasks[generator].dependsOn:
                    print subtask

        print "="*25,"\n"


    def _filter_tasks(self):
        """Select tasks specified by filter."""
        selectedTaskgen = OrderedDict()
        for filter_ in self.filter:
            if filter_ in self.tasks.iterkeys():
                selectedTaskgen[filter_] = self.tasks[filter_]
            elif filter_ in self.targets:
                selectedTaskgen[filter_] = self.targets[filter_]
            else:
                print self.targets
                raise InvalidCommand('"%s" is not a task/target.'% filter_)
        return selectedTaskgen


    def process(self):
        """Execute sub-comannd"""
        if self.list:
            return self.cmd_list()
        return self.run()

    def cmd_list(self):
        self._list_tasks(bool(self.list==2))
        return 0


    def run(self):
        """Execute tasks."""
        # get tasks dependencies on other tasks
        # add them as dependsOn the DoitTask.
        for doitTask in self.tasks.itervalues():
            if not doitTask.task:
                continue # a task that just contain subtasks.
            for dep in doitTask.task.task_dep:
                if dep not in self.tasks:
                    msg = "%s. Task dependency '%s' does not exist."
                    raise InvalidTask(msg% (doitTask.task.name,dep))
                doitTask.dependsOn.append(self.tasks[dep])

        # get target dependecies on other tasks based on file dependency on
        # a target.
        # 1) create a dictionary associating every target->task. where the task
        # is would build that target.
        for doitTask in self.tasks.itervalues():
            if not doitTask.task:
                continue
            for target in doitTask.task.targets:
                self.targets[target] = doitTask
        # 2) now go through all dependencies and check if they are target from
        # another task.
        for doitTask in self.tasks.itervalues():
            if not doitTask.task:
                continue
            for dep in doitTask.task.file_dep:
                if dep in self.targets and \
                        self.targets[dep] not in doitTask.dependsOn:
                    doitTask.dependsOn.append(self.targets[dep])

        # if no filter is defined execute all tasks
        # in the order they were defined.
        selectedTask = None
        if not self.filter:
            selectedTask = self.tasks
        # execute only tasks in the filter in the order specified by filter
        else:
            selectedTask = self._filter_tasks()

        # create a Runner instance and ...
        runner = Runner(self.dependencyFile, self.verbosity, self.alwaysExecute)

        # add to runner tasks from every selected task
        for doitTask in selectedTask.itervalues():
            doitTask.add_to(runner.add_task)

        return runner.run()

