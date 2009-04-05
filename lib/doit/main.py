"""DoIt command line program."""

import os

from doit.util import isgenerator, OrderedDict
from doit.task import InvalidTask, CmdTask, PythonTask, GroupTask
from doit.loader import Loader
from doit.runner import Runner


class InvalidCommand(Exception):
    """Invalid command line argument."""
    pass

class InvalidDodoFile(Exception):
    """Invalid dodo file"""
    pass


class DoitTask(object):
    """ 
    DoitTask helps in keeping track dependencies between tasks.

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
    
    @classmethod
    def get_tasks(cls,name,gen_result):
        """Create tasks from a task generator.

        @param name: (string) name of taskgen function
        @param gen_result: value returned by a task generator 
        @return: (tuple) task,list of subtasks
        """
        # task described as a dictionary
        if isinstance(gen_result,dict):
            if 'name' in gen_result:
                raise InvalidTask("Task %s. Only subtasks use field name."%name)

            gen_result['name'] = name
            return cls._dict_to_task(gen_result),[]

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
                tasks.append(cls._dict_to_task(task_dict))
            return None,tasks

        # if not a dictionary nor a generator. "task" is the action itself.
        return cls._dict_to_task({'name':name,'action':gen_result}),[]


    @classmethod
    def _dict_to_task(cls,task_dict):
        """Create a task instance from dictionary.
        
        @param task_dict: (dict) task representation as a dict.
        @raise L{InvalidTask}: 
        """
        # user friendly. dont go ahead with invalid input.
        for key in task_dict.keys():
            if key not in cls.TASK_ATTRS:
                raise InvalidTask("Task %s contain invalid field: %s"%
                                  (task_dict['name'],key))
            

        # check required fields
        if 'action' not in task_dict:
            raise InvalidTask("Task %s must contain field action. %s"%
                              (task_dict['name'],task_dict))

        return cls._create_task(task_dict.get('name'),
                                task_dict.get('action'),
                                task_dict.get('dependencies',[]),
                                task_dict.get('targets',[]),
                                args=task_dict.get('args',[]),
                                kwargs=task_dict.get('kwargs',{}))
        

    @staticmethod
    def _create_task(name,action,dependencies=[],targets=[],*args,**kwargs):
        """ create a BaseTask acording to action type

        @param name: (string) task name
        @param action: value dependes on the type of the task
        @param dependencies: (list of strings) each item is a file path or
        another task (prefixed with ':')
        @param targets: (list of strings) items are file paths.
        @param args: optional positional arguments for task.
        @param kwargs: optional keyword arguments for task.
        """
        # a string.
        if isinstance(action,str):
            return CmdTask(name,action,dependencies,targets)
        # a callable.
        elif callable(action):
            return PythonTask(name,action,dependencies,targets,*args,**kwargs)
        elif action is None:
            return GroupTask(name,action,dependencies,targets)
        else:
            raise InvalidTask("Invalid task type. %s:%s"%\
                                  (name,action.__class__))


    
    def add_to(self,add_cb):        
        """Add task to runner.

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
    """DoIt - load dodo file and execute tasks.

    @ivar dependencyFile: (string) file path of the dbm file.
    @ivar verbosity: (bool) verbosity level. @see L{Runner}

    @ivar list: (int) 0 dont list, run;
                      1 list task generators (do not run if listing);
                      2 list all tasks (do not run if listing);
    @ivar filter: (sequence of strings) selection of tasks to execute

    @ivar taskgen: (OrderedDict) Key: name of the function that generate tasks 
                                 Value: L{TaskGenerator} instance
    
    @ivar tasks: (OrderedDict) Key: task name ([taskgen.]name)
                               Value: L{DoitTask} instance
    @ivar targets: (dict) Key: fileName 
                          Value: L{DoitTask} instance
    """
    
    def __init__(self, dodoFile, dependencyFile, 
                 list_=False, verbosity=0, alwaysExecute=False, filter_=None):
        """Init.

        @param dodoFile: (string) path to file containing the tasks
        """
        ## intialize cmd line options
        self.dependencyFile = dependencyFile
        self.list = list_
        self.verbosity = verbosity
        self.alwaysExecute = alwaysExecute
        self.filter = filter_
        self.targets = {}

        ## load dodo file
        dodo = Loader(dodoFile)
        # file specified on dodo file are relative to itself.
        os.chdir(dodo.dir_)

        ## get task generators
        self.taskgen = OrderedDict()
        for gen in dodo.get_task_generators():
            self.taskgen[gen.name] = gen

        ## get tasks
        self.tasks = OrderedDict()
        # for each task generator
        for gen in self.taskgen.itervalues():
            task, subtasks = DoitTask.get_tasks(gen.name,gen.ref())
            subDoit = []
            # create subtasks first
            for sub in subtasks:                
                doitTask = DoitTask(sub,[])
                self.tasks[sub.name] = doitTask
                subDoit.append(doitTask)
            # create task. depends on subtasks
            self.tasks[gen.name] = DoitTask(task,subDoit)


    def _list_tasks(self, printSubtasks):
        """List task generators, in the order they were defined.
        
        @param printSubtasks: (bool) print subtasks
        """
        print "==== Tasks ===="
        for generator in self.taskgen.iterkeys():
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
        """Execute tasks."""
        # list
        if self.list:
            self._list_tasks(bool(self.list==2))
            return Runner.SUCCESS

        # get tasks dependencies on other tasks
        # task dependencies are prefixed with ":"
        # remove these entries from BaseTask instance and add them
        # as depends on on the DoitTask.
        for doitTask in self.tasks.itervalues():
            if not doitTask.task: 
                continue # a task that just contain subtasks.
            depFiles = []
            for dep in doitTask.task.dependencies:
                if dep.startswith(':'):
                    doitTask.dependsOn.append(self.tasks[dep[1:]])
                else:
                    depFiles.append(dep)
            doitTask.task.dependencies = depFiles                    
                        

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
            for dep in doitTask.task.dependencies:
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

