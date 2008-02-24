"""the doit command line program"""

import sys

from doit.core import Loader,Runner

class Main(object):
    
    def __init__(self,fileName,verbosity=0,list=False,filter=None):
        loaded = Loader(fileName)
        # list of functions that generate tasks
        self.generator = loaded.getTaskGenerators()

        # also put them in a dictionary with name as key
        self.tasks = {}
        for f in self.generator:
            self.tasks[f.name] = f

        self.list = list
        self.filter = filter
        self.verbosity = verbosity

    def _list_generators(self):
        """list task generators, in the order they were defined"""
        print "==== Task Generators ===="
        for f in self.generator:
            print f.name
        print "="*25,"\n"

    def _filter_tasks(self):
        """select tasks specified by filter"""
        selectedTasks = []
        for f in self.filter:
            if f in self.tasks:
                selectedTasks.append(self.tasks[f])
            else:
                #TODO document this
                raise Exception('"%s" is not a task'%f)
        return selectedTasks

    def process(self):
        """ process it according to given parameters"""
        # list
        if self.list:
            self._list_generators()

        # if no filter is defined execute all tasks 
        # in the order they were defined.
        selectedTasks = None
        if not self.filter:
            selectedTasks = self.generator
        # execute only tasks in the filter in the order specified by filter
        else:
            selectedTasks = self._filter_tasks()

        # create a Runner instance and ...
        runner = Runner(self.verbosity)
        # tasks from every task generator.
        for f in selectedTasks:
            runner.addTask(f.ref(),f.name)
        return runner.run()
        
def main(fileName, **kargs):
    m = Main(fileName, **kargs)
    return m.process()
