"""Task runner."""

import sys
import traceback

from doit import logger
from doit.task import TaskFailed
from doit.dependency import Dependency

#: execution result.
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
    errorException = None  # Exception instance, in case of error
    result = SUCCESS
    setup_loaded = set() # setups that were loaded already.

    for task in tasks:
        # clear previous output
        #TODO should find a way to put this on the bottom
        logger.clear('stdout')
        logger.clear('stderr')

        # check if task is up-to-date
        try:
            task_uptodate, task.dep_changed = dependencyManager.up_to_date(
                task.name, task.file_dep, task.targets, task.run_once)
        # TODO: raise an exception here.
        except:
            print
            print "ERROR checking dependencies for: %s"% task.title()
            result = ERROR
            break

        # if task id up to date just print title
        if not alwaysExecute and task_uptodate:
            print "---", task.title()
        else:
            print task.title()

            try:
                # setup env
                for setup_obj in task.setup:
                    if setup_obj in setup_loaded:
                        continue
                    setup_loaded.add(setup_obj)
                    if hasattr(setup_obj, 'setup'):
                        setup_obj.setup()
                # finally execute it
                task.execute(capture_stdout, capture_stderr)
                #save execution successful
                if task.run_once:
                    dependencyManager.save_run_once(task.name)
                dependencyManager.save_dependencies(task.name,task.file_dep)

            # in python 2.4 SystemExit and KeyboardInterrupt subclass
            # from Exception.
            # specially a problem when the a fork from the main process
            # exit using sys.exit() instead of os._exit().
            except (SystemExit, KeyboardInterrupt), exp:
                raise

            # task failed
            except TaskFailed:
                logger.log("stderr", '\nTask failed => %s\n'% task.name)
                result = FAILURE
                break

            # task error
            except Exception, exception:
                logger.log("stderr", '\nTask error => %s\n'% task.name)
                result = ERROR
                errorException = exception
                break

    ## done
    # flush update dependencies
    dependencyManager.close()

    # if test fails print output from failed task
    if result != SUCCESS:
        logger.flush('stdout',sys.stdout)
        logger.flush('stderr',sys.stderr)

    # in case of error show traceback from last exception
    if result == ERROR:
        line = "="*40 + "\n"
        sys.stderr.write(line)
        if errorException and hasattr(errorException, "originalException"):
            sys.stderr.write("\n".join(errorException.originalException))
        else:
            sys.stderr.write(traceback.format_exc())

    # run tasks cleanup.
    for setup in setup_loaded:
        if hasattr(setup, 'cleanup'):
            try:
                setup.cleanup()
            # not sure what should be the behaviour of errors on
            # cleanup.
            # report error but keep result as successful.
            except Exception, e:
                sys.stderr.write(traceback.format_exc())

    return result
