"""Task runner."""

import sys
import traceback
from subprocess import PIPE

from doit import CatchedException, TaskFailed, SetupError, DependencyError
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
            raise SetupError("ERROR on object setup", exception)


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

class ConsoleReporter(object):

    def __init__(self):
        # save non-succesful result information
        self.results = []


    def start_task(self, task):
        print task.title()


    def complete_task(self, task, exception):
        self.results.append({'task': task, 'exception':exception})


    def skip_uptodate(self, task):
        print "---", task.title()


    def complete_run(self):
        # if test fails print output from failed task
        for result in self.results:
            sys.stderr.write("#"*40 + "\n")
            sys.stderr.write('%s: %s\n' % (result['exception'].get_name(),
                                           result['task'].name))
            sys.stderr.write(result['exception'].get_msg())
            sys.stderr.write("\n")
            task = result['task']
            out = "".join([a.out for a in task.actions if a.out])
            sys.stderr.write("%s\n" % out)
            err = "".join([a.err for a in task.actions if a.err])
            sys.stderr.write("%s\n" % err)


    def final_result(self):
        if not self.results:
            return SUCCESS
        else:
            # only return FAILURE if no errors happened.
            for result in self.results:
                if not isinstance(result['exception'], TaskFailed):
                    return ERROR
            return FAILURE




def run_tasks(dependencyFile, tasks, verbosity=1, alwaysExecute=False,
              reporter=ConsoleReporter):
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
    if verbosity < 2:
        task_stdout = PIPE #capture
    else:
        task_stdout = None #use parent process
    if verbosity == 0:
        task_stderr = PIPE
    else:
        task_stderr = None
    dependencyManager = Dependency(dependencyFile)
    setupManager = SetupManager()
    resultReporter = reporter()

    for task in tasks:
        try:
            # check if task is up-to-date
            try:
                task_uptodate, task.dep_changed = dependencyManager.up_to_date(
                    task.name, task.file_dep, task.targets, task.run_once)
            except Exception, exception:
                raise DependencyError("ERROR checking dependencies", exception)

            # if task id up to date just print title
            if not alwaysExecute and task_uptodate:
                resultReporter.skip_uptodate(task)
                continue

            # setup env
            for setup_obj in task.setup:
                setupManager.load(setup_obj)

            # finally execute it!
            resultReporter.start_task(task)
            task.execute(task_stdout, task_stderr)

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

        # task error
        except CatchedException, exception:
            resultReporter.complete_task(task, exception)
            break


    ## done
    # flush update dependencies
    dependencyManager.close()
    # clean setup objects
    setupManager.cleanup()

    # report final results
    resultReporter.complete_run()
    return resultReporter.final_result()
