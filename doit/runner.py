"""Task runner."""

import sys

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

        except (SystemExit, KeyboardInterrupt): raise
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
                    raise SetupError("ERROR on setup_obj cleanup", e)


# execution result.
SUCCESS = 0
FAILURE = 1
ERROR = 2

class Runner(object):
    """Task runner

    """
    def __init__(self, dependencyFile, reporter):
        """@param dependencyFile: (string) file path of the db file
        @param reporter: reporter to be used. It can be a class or an object
        """
        self.dependencyManager = Dependency(dependencyFile)
        self.reporter = reporter
        self.setupManager = SetupManager()
        self.final_result = SUCCESS # until something fails


    def execute_task(self, task, verbosity):
        # setup env
        for setup_obj in task.setup:
            self.setupManager.load(setup_obj)

        # finally execute it!
        self.reporter.execute_task(task)
        task.execute(sys.stdout, sys.stderr, verbosity)


    def run_tasks(self, tasks, verbosity=None, alwaysExecute=False,
                  continue_=False):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param tasks: (list) - L{Task} tasks to be executed
        @param verbosity: (int) 0,1,2 see Task.execute
        @param alwaysExecute: (bool) execute even if up-to-date
        @param continue_: (bool) execute all tasks even after a task failure
        """
        for task in tasks:
            self.reporter.start_task(task)
            try:
                # check if task is up-to-date
                try:
                    task_uptodate = self.dependencyManager.get_status(task)
                except Exception, exception:
                    raise DependencyError("ERROR checking dependencies", exception)

                # if task is up-to-date skip it
                if not alwaysExecute and (task_uptodate=='up-to-date') :
                    self.reporter.skip_uptodate(task)
                    continue

                # check if task should be ignored (user controlled)
                if not alwaysExecute and (task_uptodate=='ignore') :
                    self.reporter.skip_ignore(task)
                    continue

                # get values from other tasks
                for arg, value in task.getargs.iteritems():
                    try:
                        task.options[arg] = self.dependencyManager.get_value(value)
                    except Exception, exception:
                        msg = ("ERROR getting value for argument '%s'\n" % arg +
                               str(exception))
                        raise DependencyError(msg)

                self.execute_task(task, verbosity)

                # save execution successful
                self.dependencyManager.save_success(task)
                self.reporter.add_success(task)

            # in python 2.4 SystemExit and KeyboardInterrupt subclass
            # from Exception.
            # specially a problem when a fork from the main process
            # exit using sys.exit() instead of os._exit().
            except (SystemExit, KeyboardInterrupt):
                raise

            # task error
            except CatchedException, exception:
                self.dependencyManager.remove_success(task)
                self.reporter.add_failure(task, exception)
                # only return FAILURE if no errors happened.
                if isinstance(exception, TaskFailed):
                    self.final_result = FAILURE
                else:
                    self.final_result = ERROR
                if not continue_:
                    break

    def finish(self):
        """finish running tasks"""
        # flush update dependencies
        self.dependencyManager.close()
        # clean setup objects
        try:
            self.setupManager.cleanup()
        except SetupError, e:
            self.reporter.cleanup_error(e)

        # report final results
        self.reporter.complete_run()
        return self.final_result
