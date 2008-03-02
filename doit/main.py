"""the doit command line program"""

import os

from odict import OrderedDict

from doit.util import isgenerator
from doit.core import Runner, InvalidTask, CmdTask, PythonTask
from doit.loader import Loader


def _create_task(name,action,dependencies=[],**kwargs):
    """ create a TaskInstance acording to action type"""
    
    # a list. execute as a cmd    
    if isinstance(action,list) or isinstance(action,tuple):
        return CmdTask(name,action,dependencies)
    # a string. split and execute as a cmd
    elif isinstance(action,str):
        return CmdTask(name,action.split(),dependencies)
    # a callable.
    elif callable(action):
        return PythonTask(name,action,dependencies,**kwargs)
    else:
        raise InvalidTask("Invalid task type. %s:%s"%(name,action.__class__))

def _get_tasks(name,task):
    """@return list tasks instances """

    # task described as a dictionary
    if isinstance(task,dict):
        # check valid input
        if 'action' not in task:
            raise InvalidTask("Task %s must contain field action. %s"%
                              (name,task))

        return [_create_task(name,task.get('action'),
                             task.get('dependencies',[]),
                             args=task.get('args',[]),
                             kwargs=task.get('kwargs',{}))]

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
            if 'action' not in t:
                raise InvalidTask("Task %s must contain field action. %s"%
                                  (name,t))

            tasks.append(_create_task("%s.%s"%(name,t.get('name')), 
                                      t.get('action'),
                                      t.get('dependencies',[])))
        return tasks

    # if not a dictionary nor a generator. "task" is the action itself.
    return [_create_task(name, task)]




class Main(object):
    
    def __init__(self, fileName, list=False, verbosity=0,filter=None):
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
                #TODO document this
                raise Exception('"%s" is not a task'%f)
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
        runner = Runner(self.verbosity)
        # tasks from every task generator.
        for g in selectedTaskgen.itervalues():
            for subtask in _get_tasks(g.name,g.ref()):
                runner._addTask(subtask)

        return runner.run()

