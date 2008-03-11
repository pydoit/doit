"""the doit command line program"""

import os

from odict import OrderedDict

from doit.util import isgenerator
from doit.task import InvalidTask, CmdTask, PythonTask
from doit.loader import Loader
from doit.runner import Runner


class InvalidCommand(Exception):pass
# sequence of know attributes(keys) of a task dict.
TASK_ATTRS = ('name','action','dependencies','targets','args','kwargs')

def dict_to_task(task_dict):
    """ return task instance from dictionary
    check for errors in input dict and calls _create_task"""
    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))
            

    # check required fields
    if 'action' not in task_dict:
        raise InvalidTask("Task %s must contain field action. %s"%
                          (task_dict['name'],task_dict))

    return _create_task(task_dict.get('name'),
                        task_dict.get('action'),
                        task_dict.get('dependencies',[]),
                        task_dict.get('targets',[]),
                        args=task_dict.get('args',[]),
                        kwargs=task_dict.get('kwargs',{}))
        

def _create_task(name,action,dependencies=[],targets=[],*args,**kwargs):
    """ create a TaskInstance acording to action type"""
    
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
        raise InvalidTask("Invalid task type. %s:%s"%(name,action.__class__))


def _get_tasks(name,task):
    """@return list tasks instances """
    # task described as a dictionary
    if isinstance(task,dict):
        #FIXME name parameter can not be given
        task['name'] = name
        return [dict_to_task(task)]

    # a generator
    if isgenerator(task):
        tasks = []
        for t in task:
            # check valid input
            if not isinstance(t,dict):
                raise InvalidTask("Task %s must yield dictionaries"%name)

            if 'name' not in t:
                raise InvalidTask("Task %s must contain field name. %s"%
                                  (name,t))
            # name is task.subtask
            t['name'] = "%s.%s"%(name,t.get('name'))
            tasks.append(dict_to_task(t))
        return tasks

    # if not a dictionary nor a generator. "task" is the action itself.
    # FIXME name parameter can not be given
    return [dict_to_task({'name':name,'action':task})]




class Main(object):
    
    def __init__(self, fileName, dependencyFile, 
                 list=False, verbosity=0,filter=None):
        self.dependencyFile = dependencyFile
        self.list = list
        self.verbosity = verbosity
        self.filter = filter

        # dictionary of functions that generate tasks with name as key
        self.taskgen = OrderedDict()

        loaded = Loader(fileName)
        # file specified on dodo file are relative to itself.
        os.chdir(loaded.dir_)

        for g in loaded.getTaskGenerators():
            self.taskgen[g.name] = g


    def _list_generators(self):
        """list task generators, in the order they were defined"""
        print "==== Task Generators ===="
        for g in self.taskgen.iterkeys():
            print g
        print "="*25,"\n"


    def _filter_taskgen(self):
        """select tasks specified by filter"""
        selectedTaskgen = OrderedDict()
        for f in self.filter:
            if f in self.taskgen.iterkeys():
                selectedTaskgen[f] = self.taskgen[f]
            else:
                raise InvalidCommand('"%s" is not a task.'%f)
        return selectedTaskgen
        
    

    def process(self):
        """ process it according to given parameters"""
        # list
        if self.list:
            self._list_generators()
            return Runner.SUCCESS

        # if no filter is defined execute all tasks 
        # in the order they were defined.
        selectedTaskgen = None
        if not self.filter:
            selectedTaskgen = self.taskgen
        # execute only tasks in the filter in the order specified by filter
        else:
            selectedTaskgen = self._filter_taskgen()

        # create a Runner instance and ...
        runner = Runner(self.dependencyFile, self.verbosity)
        # tasks from every task generator.
        for g in selectedTaskgen.itervalues():
            for subtask in _get_tasks(g.name,g.ref()):
                runner._addTask(subtask)

        return runner.run()

