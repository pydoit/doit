"""Task runner."""

import sys, traceback

from doit import logger
from doit.util import OrderedDict
from doit.task import BaseTask, InvalidTask, TaskFailed
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
        self.alwaysExecute = alwaysExecute
        self._tasks = OrderedDict()
        BaseTask.CAPTURE_OUT = verbosity < 2
        BaseTask.CAPTURE_ERR = verbosity == 0

    def add_task(self,task):
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

    def run(self):
        """Execute all tasks."""
        
        dependencyManager = Dependency(self.dependencyFile)
        errorException = None
        result = self.SUCCESS 

        for task in self._tasks.itervalues():
            # clear previous output
            logger.clear('stdout')
            logger.clear('stderr')

            # check if task is up-to-date
            try:
                task_uptodate = dependencyManager.up_to_date(task.name, 
                                              task.dependencies, task.targets)
            #TODO: raise an exception here.
            except:
                print
                print "ERROR checking dependencies for: %s"% task.title()
                result = self.ERROR
                break

            # if task id up to date just print title
            if not self.alwaysExecute and task_uptodate:
                print "---", task.title()
            else:
                print task.title()
                try:
                    task.execute()
                # task failed
                except TaskFailed:
                    logger.log("stdout", 'Task failed\n')
                    result = self.FAILURE
                    break
                # task error
                except Exception, exception:
                    logger.log("stdout", 'Task error\n')
                    result = self.ERROR
                    errorException = exception
                    break              
                # task success - save dependencies
                else:
                    dependencyManager.save_dependencies(task.name,
                                                        task.dependencies)
                    dependencyManager.save_dependencies(task.name, task.targets)
                
            
        ## done 
        # flush update dependencies 
        dependencyManager.close()

        # if test fails print output from failed task
        if result != self.SUCCESS:
            logger.flush('stdout',sys.stdout)
            logger.flush('stderr',sys.stderr)
        
        # in case of error show traceback from last exception
        if result == self.ERROR:
            line = "="*40 + "\n"
            sys.stderr.write(line)
            if errorException and hasattr(errorException, "originalException"):
                sys.stderr.write("\n".join(errorException.originalException))
            else:
                sys.stderr.write(traceback.format_exc())
        
        return result
