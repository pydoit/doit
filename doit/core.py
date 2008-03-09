import sys, traceback

from odict import OrderedDict

from doit import logger
from doit.task import BaseTask, InvalidTask, TaskFailed, TaskError
from doit.dependency import Dependency


class Runner(object):
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2

    def __init__(self, dependencyFile, verbosity=1):
        """
        verbosity
        # 0 => print (stderr and stdout) from failed tasks
        # 1 => print stderr and (stdout from failed tasks)
        # 2 => print stderr and stdout from all tasks
        """
        self.dependencyFile = dependencyFile
        self.verbosity = verbosity
        self._tasks = OrderedDict()
        
        BaseTask.CAPTURE_OUT = verbosity < 2
        BaseTask.CAPTURE_ERR = verbosity == 0

    def _addTask(self,task):
        # task must be a BaseTask
        if not isinstance(task,BaseTask):
            raise InvalidTask("Task must an instance of BaseTask class. %s"% 
                              (task.__class__))

        #task name must be unique
        if task.name in self._tasks:
            raise InvalidTask("Task names must be unique. %s"%task.name)
        # add
        self._tasks[task.name] = task

    def run(self, printTitle=True):
        """
        @param dependencyFile string 
        @param print_title bool print task title """
        dependencyManager = Dependency(self.dependencyFile)
        result = self.SUCCESS 

        for task in self._tasks.itervalues():
            # clear previous output
            logger.clear('stdout')
            logger.clear('stderr')

            try:                
                if dependencyManager.up_to_date(task.name,task.dependencies):
                    if printTitle:
                        print "---", task.title()
                else:
                    if printTitle:
                        print task.title()
                    task.execute()
                    dependencyManager.save_dependencies(task.name,task.dependencies)
            # task failed
            except TaskFailed:
                logger.log("stdout", 'Task failed\n')
                result = self.FAILURE
                break
            # task error
            except TaskError:
                logger.log("stdout", 'Task error\n')
                result = self.ERROR
                break                
        
        ## done
        # flush update dependencies 
        dependencyManager.close()

        # if test fails print output from failed task
        if result != self.SUCCESS:
            logger.flush('stdout',sys.stdout)
            logger.flush('stderr',sys.stderr)
        
        # always show traceback for whatever exception
        if result == self.ERROR:
            # FIXME. traceback for the original exception.
            sys.stderr.write(traceback.format_exc())
        
        return result
