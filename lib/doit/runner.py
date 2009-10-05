"""Task runner."""

import sys
import traceback

from doit import logger
from doit import TaskFailed, TaskError, SetupError, DependencyError
from doit.dependency import Dependency


class SetupManager(object):
    """Manage setup objects

    Setup object is any object that implements 'setup' and/or 'cleanup'
    @ivar _loaded (list): of loaded setup objects
    """

    def __init__(self):
        self._loaded = set()


    def load(self, setup_obj):
        """run setup from a setup_obj if it is not loaded yet"""
        if setup_obj in self._loaded:
            return

        try:
            self._loaded.add(setup_obj)
            if hasattr(setup_obj, 'setup'):
                setup_obj.setup()
        except Exception, exception:
            raise SetupError(exception)


    def cleanup(self):
        """run cleanup for all loaded objects"""
        for setup_obj in self._loaded:
            if hasattr(setup_obj, 'cleanup'):
                try:
                    setup_obj.cleanup()
                # report error but keep result as successful.
                except Exception, e:
                    sys.stderr.write(traceback.format_exc())



# execution result.
SUCCESS = 0
FAILURE = 1
ERROR = 2

def run_tasks(dependencyFile, tasks, verbosity=1, alwaysExecute=False):
    """This will actually run/execute the tasks.
    It will check file dependencies to decide if task should be executed
    and save info on successful runs.
    It also deals with output to stdout/stderr.

    @param dependencyFile: (string) file path of the db file
    @param tasks: (list) - L{Task} tasks to be executed
    @param verbosity:
     - 0 => print (stderr and stdout) from failed tasks
     - 1 => print stderr and (stdout from failed tasks)
     - 2 => print stderr and stdout from all tasks
    @param alwaysExecute: (bool) execute even if up-to-date
    """
    capture_stdout = verbosity < 2
    capture_stderr = verbosity == 0
    dependencyManager = Dependency(dependencyFile)
    setupManager = SetupManager()
    results = [] # save non-succesful result information

    for task in tasks:
        # clear previous output
        #TODO should find a way to put this on the bottom
        logger.clear('stdout')
        logger.clear('stderr')
        try:
            # check if task is up-to-date
            try:
                task_uptodate, task.dep_changed = dependencyManager.up_to_date(
                    task.name, task.file_dep, task.targets, task.run_once)
            except Exception, exception:
                raise DependencyError("ERROR checking dependencies", exception)

            # if task id up to date just print title
            if not alwaysExecute and task_uptodate:
                print "---", task.title()
                continue

            # going to execute the task...
            print task.title()

            # setup env
            for setup_obj in task.setup:
                setupManager.load(setup_obj)

            # finally execute it!
            task.execute(capture_stdout, capture_stderr)

            #save execution successful
            if task.run_once:
                dependencyManager.save_run_once(task.name)
            dependencyManager.save_dependencies(task.name,task.file_dep)

        # in python 2.4 SystemExit and KeyboardInterrupt subclass
        # from Exception.
        # specially a problem when a fork from the main process
        # exit using sys.exit() instead of os._exit().
        except (SystemExit, KeyboardInterrupt), exp:
            raise

        # task error # Exception is necessary for setup errors
        except (TaskError, SetupError, TaskFailed, DependencyError), exception:
            results.append({'task': task, 'exception': exception})
            break


    ## done
    # flush update dependencies
    dependencyManager.close()

    # if test fails print output from failed task
    if results:
        logger.flush('stdout',sys.stdout)
        logger.flush('stderr',sys.stderr)
        for res in results:
            sys.stderr.write('\nTask => %s\n' % res['task'].name)
            # in case of error show traceback
            if 'exception' in res:
                sys.stderr.write("#"*40 + "\n")
                sys.stderr.write(res['exception'].get_msg())

    setupManager.cleanup()

    # there is not distcition between errors and failures on returned result
    if not results:
        return SUCCESS
    else:
        return ERROR

