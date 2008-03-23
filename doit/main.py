"""the doit command line program"""

import os

from odict import OrderedDict

from doit.util import isgenerator
from doit.task import InvalidTask, CmdTask, PythonTask
from doit.loader import Loader
from doit.runner import Runner


class InvalidCommand(Exception):pass

class DoitTask(object):
    """ 
    DoitTask helps in keeping track dependencies between tasks.

    @ivar dependsOn {list of string}: note that dependencies here are tasks only
                                      not files, as in BaseTask
    @ivar task {BaseTask}: the task itself
    @ivar state {choice}: 
           UNUSED -> task not used 
           ADDING -> adding dependencies (used to detect cyclic dependency).
           ADDED -> task already added to runner.
    """
    # sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','action','dependencies','targets','args','kwargs')

    UNUSED = 0
    ADDING = 1
    ADDED = 2



    def __init__(self, task, dependsOn=[]):
        self.task = task
        self.dependsOn = dependsOn
    
    @classmethod
    def get_tasks(cls,name,gen_result):
        """
        @param name {string}: name of taskgen function
        @param gen_result: value returned by a task generator 
        @return task,list subtasks
        """
        # task described as a dictionary
        if isinstance(gen_result,dict):
            # FIXME name parameter can not be given
            gen_result['name'] = name
            return cls._dict_to_task(gen_result),[]

        # a generator
        if isgenerator(gen_result):
            tasks = []
            # the generator return subtasks.
            for t in gen_result:
                # check valid input
                if not isinstance(t,dict):
                    raise InvalidTask("Task %s must yield dictionaries"%name)

                if 'name' not in t:
                    raise InvalidTask("Task %s must contain field name. %s"%
                                  (name,t))
                # name is task.subtask
                t['name'] = "%s:%s"%(name,t.get('name'))
                tasks.append(cls._dict_to_task(t))
            return None,tasks

        # if not a dictionary nor a generator. "task" is the action itself.
        return cls._dict_to_task({'name':name,'action':gen_result}),[]

    @classmethod
    def _dict_to_task(cls,task_dict):
        """ return task instance from dictionary
        check for errors in input dict and calls _create_task"""
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
        """ create a BaseTask acording to action type"""
    
        # a list. execute as a cmd    
        if isinstance(action,list) or isinstance(action,tuple):
            return CmdTask(name,action,dependencies,targets)
        # a string. split and execute as a cmd
        elif isinstance(action,str):
            return CmdTask(name,action.split(),dependencies,targets)
        # a callable.
        elif callable(action):
            return PythonTask(name,action,dependencies,targets,*args,**kwargs)
        else:
            raise InvalidTask("Invalid task type. %s:%s"%\
                                  (name,action.__class__))





class Main(object):
    """
    runtime options:
    ---------------
    @ivar dependencyFile {string}: file path of the dbm file.
    @ivar list {int}: 0 dont list, run
                      1 list task generators (do not run if listing)
                      2 list all tasks (do not run if listing)
    @ivar verbosity {bool}: verbosity level. @see Runner
    @ivar filter {sequence of strings}: selection of tasks to execute

    @ivar taskgen {OrderedDict}: Key: name of the function that generate tasks 
                                 Value: TaskGen instance
    
    @ivar tasks {OrderedDict}: Key: task name ([taskgen.]name)
                               Value: DoitTask instance
    """
    
    def __init__(self, dodoFile, dependencyFile, 
                 list=False, verbosity=0,filter=None):
        """
        @param dodoFile {string} path to file containing the tasks
        """
        ## intialize cmd line options
        self.dependencyFile = dependencyFile
        self.list = list
        self.verbosity = verbosity
        self.filter = filter

        ## load dodo file
        dodo = Loader(dodoFile)
        # file specified on dodo file are relative to itself.
        os.chdir(dodo.dir_)

        # get task generators
        self.taskgen = OrderedDict()
        for g in dodo.getTaskGenerators():
            self.taskgen[g.name] = g

        ## get tasks
        self.tasks = OrderedDict()
        # for each task generator
        for g in self.taskgen.itervalues():
            task, subtasks = DoitTask.get_tasks(g.name,g.ref())
            self.tasks[g.name] = DoitTask(task,[s.name for s in subtasks])
            for s in subtasks:
                self.tasks[s.name] = DoitTask(s)

    def _list_tasks(self, printSubtasks):
        """list task generators, in the order they were defined"""
        print "==== Tasks ===="
        for g in self.taskgen.iterkeys():
            print g
            # print subtasks  
            if printSubtasks:
                for t in self.tasks[g].dependsOn:
                    print t

        print "="*25,"\n"


    def _filter_tasks(self):
        """select tasks specified by filter"""
        selectedTaskgen = OrderedDict()
        for f in self.filter:
            if f in self.tasks.iterkeys():
                selectedTaskgen[f] = self.tasks[f]
            else:
                raise InvalidCommand('"%s" is not a task.'%f)
        return selectedTaskgen
        


    def process(self):
        """ process it according to given parameters"""
        # list
        if self.list:
            self._list_tasks(bool(self.list==2))
            return Runner.SUCCESS

        # if no filter is defined execute all tasks 
        # in the order they were defined.
        selectedTask = None
        if not self.filter:
            selectedTask = self.tasks
        # execute only tasks in the filter in the order specified by filter
        else:
            selectedTask = self._filter_tasks()

        # create a Runner instance and ...
        runner = Runner(self.dependencyFile, self.verbosity)

        # tasks from every task generator.
        for name,t in selectedTask.iteritems():
            # add dependencies
            for ti in t.dependsOn:
                # dont add a task twice
                if ti not in runner._tasks:
                    runner._addTask(self.tasks[ti].task)
            
            # add itself
            if t.task:
                if name not in runner._tasks:
                    runner._addTask(t.task)

        return runner.run()

