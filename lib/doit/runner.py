"""Task runner."""

import sys, traceback

from odict import OrderedDict

from doit import logger
from doit.task import BaseTask, InvalidTask, TaskFailed, TaskError
from doit.dependency import Dependency


class Runner(object):
    """Run tasks.

    @cvar SUCCESS: execution result.
    @cvar FAILURE: execution result.
    @cvar ERROR: execution result.

    @ivar dependencyFile: (string) file path of the dbm file.
    @ivar verbosity:
     - 0 => print (stderr and stdout) from failed tasks
     - 1 => print stderr and (stdout from failed tasks)
     - 2 => print stderr and stdout from all tasks
    @ivar alwaysExecute: (bool) execute even if up-to-date
    @ivar _tasks: (OrderedDictionary) tasks to be executed.
    key:task name; value:L{BaseTask} instance
    """
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2

    def __init__(self, dependencyFile, verbosity=1, alwaysExecute=False):
        """Init."""
        self.dependencyFile = dependencyFile
        self.verbosity = verbosity
        self.alwaysExecute = alwaysExecute
        self._tasks = OrderedDict()
        
        BaseTask.CAPTURE_OUT = verbosity < 2
        BaseTask.CAPTURE_ERR = verbosity == 0

    def _addTask(self,task):
        """Add a task to be run.

        @param task: (L{BaseTask}) instance.
        @raise InvalidTask: 
        """
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
        """Execute all tasks.

        @param printTitle: (bool) print task title
        """
        dependencyManager = Dependency(self.dependencyFile)
        result = self.SUCCESS 

        for task in self._tasks.itervalues():
            # clear previous output
            logger.clear('stdout')
            logger.clear('stderr')

            try:                
                if not self.alwaysExecute and \
                        dependencyManager.up_to_date(task.name,
                                       task.dependencies, task.targets):
                    if printTitle:
                        print "---", 
                else:
                    task.execute()
                    dependencyManager.save_dependencies(task.name,
                                                        task.dependencies)
                    dependencyManager.save_dependencies(task.name,
                                                        task.targets)

            # task failed
            except TaskFailed:
                logger.log("stdout", 'Task failed\n')
                result = self.FAILURE
                break
            # task error
            except:
                logger.log("stdout", 'Task error\n')
                result = self.ERROR
                break              
            finally:
                if printTitle:
                    print task.title()
            
        ## done
        # flush update dependencies 
        dependencyManager.close()

        # if test fails print output from failed task
        if result != self.SUCCESS:
            logger.flush('stdout',sys.stdout)
            logger.flush('stderr',sys.stderr)
        
        # always show traceback for whatever exception
        if result == self.ERROR:
            title = "="*40 + "\n"
            sys.stderr.write(title)
            sys.stderr.write(traceback.format_exc())
        
        return result
