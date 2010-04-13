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

        self._loaded.add(setup_obj)
        if hasattr(setup_obj, 'setup'):
            setup_obj.setup()


    def cleanup(self):
        """run cleanup for all loaded objects"""
        for setup_obj in self._loaded:
            if hasattr(setup_obj, 'cleanup'):
                try:
                    setup_obj.cleanup()
                # report error but keep result as successful.
                # FIXME should execute all cleanup's even with errors
                # TODO caller should handle the exception
                except Exception, e:
                    return SetupError("ERROR on setup_obj cleanup", e)


# execution result.
SUCCESS = 0
FAILURE = 1
ERROR = 2

class Runner(object):
    """Task runner

    """
    def __init__(self, dependencyFile, reporter, continue_=False,
                 always_execute=False):
        """@param dependencyFile: (string) file path of the db file
        @param reporter: reporter to be used. It can be a class or an object
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        """
        self.dependencyManager = Dependency(dependencyFile)
        self.reporter = reporter
        self.continue_ = continue_
        self.always_execute = always_execute

        self.setupManager = SetupManager()
        self.final_result = SUCCESS # until something fails
        self._stop_running = False


    def select_task(self, task):
        """Returns bool, task should be executed
         * side-effect: set task.options
        """
        self.reporter.start_task(task)
        # check if task is up-to-date
        try:
            task_uptodate = self.dependencyManager.get_status(task)
        except Exception, exception:
            de = DependencyError("ERROR checking dependencies", exception)
            self.handle_task_error(task, de)
            return False

        if not self.always_execute:
            # if task is up-to-date skip it
            if task_uptodate == 'up-to-date':
                self.reporter.skip_uptodate(task)
                return False
            # check if task should be ignored (user controlled)
            if task_uptodate == 'ignore':
                self.reporter.skip_ignore(task)
                return False

        # get values from other tasks
        for arg, value in task.getargs.iteritems():
            try:
                task.options[arg] = self.dependencyManager.get_value(value)
            except Exception, exception:
                msg = ("ERROR getting value for argument '%s'\n" % arg +
                       str(exception))
                self.handle_task_error(task, DependencyError(msg))
                return False
        return True


    def execute_task(self, task, verbosity):
        # setup env
        for setup_obj in task.setup:
            try:
                self.setupManager.load(setup_obj)
            except (SystemExit, KeyboardInterrupt): raise
            except Exception, exception:
                return SetupError("ERROR on object setup", exception)

        # finally execute it!
        self.reporter.execute_task(task)
        return task.execute(sys.stdout, sys.stderr, verbosity)


    def process_task_result(self, task, catched_excp):
        # save execution successful
        if catched_excp is None:
            self.dependencyManager.save_success(task)
            self.reporter.add_success(task)
        # task error
        else:
            self.handle_task_error(task, catched_excp)


    def handle_task_error(self, task, catched_excp):
        assert isinstance(catched_excp, CatchedException)
        self.dependencyManager.remove_success(task)
        self.reporter.add_failure(task, catched_excp)
        # only return FAILURE if no errors happened.
        if isinstance(catched_excp, TaskFailed):
            self.final_result = FAILURE
        else:
            self.final_result = ERROR
        if not self.continue_:
            self._stop_running = True


    def run_tasks(self, tasks, verbosity=None):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param tasks: (list) - L{Task} tasks to be executed
        @param verbosity: (int) 0,1,2 see Task.execute
        """
        for task in tasks:
            if self._stop_running:
                break
            if not self.select_task(task):
                continue
            catched_excp = self.execute_task(task, verbosity)
            self.process_task_result(task, catched_excp)


    def finish(self):
        """finish running tasks"""
        # flush update dependencies
        self.dependencyManager.close()
        # clean setup objects
        error = self.setupManager.cleanup()
        if error:
            self.reporter.cleanup_error(error)

        # report final results
        self.reporter.complete_run()
        return self.final_result
