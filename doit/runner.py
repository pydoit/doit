"""Task runner."""

import sys

from doit.exceptions import CatchedException
from doit.exceptions import TaskFailed, SetupError, DependencyError
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

    run_tasks():
        for each task:
            select_task()
            execute_task()
            process_task_result()
    finish()

    """
    def __init__(self, dependencyFile, reporter, continue_=False,
                 always_execute=False, verbosity=0):
        """@param dependencyFile: (string) file path of the db file
        @param reporter: reporter to be used. It can be a class or an object
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param verbosity: (int) 0,1,2 see Task.execute
        """
        self.dependencyManager = Dependency(dependencyFile)
        self.reporter = reporter
        self.continue_ = continue_
        self.always_execute = always_execute
        self.verbosity = verbosity

        self.setupManager = SetupManager()
        self.teardown_list = [] # list of tasks to be teardown
        self.final_result = SUCCESS # until something fails
        self._stop_running = False


    def _handle_task_error(self, task, catched_excp):
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


    def select_task(self, task):
        """Returns bool, task should be executed
         * side-effect: set task.options
        """

        # check if run_status was already calculated
        if task.run_status is None:
            # TODO reporter.start_task rename to get_status
            self.reporter.start_task(task)
            # check if task is up-to-date
            try:
                task.run_status = self.dependencyManager.get_status(task)
            except Exception, exception:
                de = DependencyError("ERROR checking dependencies", exception)
                self._handle_task_error(task, de)
                return False

            if not self.always_execute:
                # if task is up-to-date skip it
                if task.run_status == 'up-to-date':
                    self.reporter.skip_uptodate(task)
                    return False
                # check if task should be ignored (user controlled)
                if task.run_status == 'ignore':
                    self.reporter.skip_ignore(task)
                    return False

            if task.setup_tasks:
                # dont execute now, execute setup first...
                return False
        else:
            assert task.run_status == 'run'
            # check if already executed
            if not task.setup_tasks:
                return False

        # selected just need to get values from other tasks
        for arg, value in task.getargs.iteritems():
            try:
                task.options[arg] = self.dependencyManager.get_value(value)
            except Exception, exception:
                msg = ("ERROR getting value for argument '%s'\n" % arg +
                       str(exception))
                self._handle_task_error(task, DependencyError(msg))
                return False

        return True


    def execute_task(self, task):
        """execute task's actions"""
        # setup env
        for setup_obj in task.setup:
            try:
                self.setupManager.load(setup_obj)
            except (SystemExit, KeyboardInterrupt): raise
            except Exception, exception:
                return SetupError("ERROR on object setup", exception)

        # new style cleanup/teardown
        if task.teardown:
            self.teardown_list.append(task)

        # finally execute it!
        self.reporter.execute_task(task)
        return task.execute(sys.stdout, sys.stderr, self.verbosity)


    def process_task_result(self, task, catched_excp):
        # save execution successful
        if catched_excp is None:
            self.dependencyManager.save_success(task)
            self.reporter.add_success(task)
        # task error
        else:
            self._handle_task_error(task, catched_excp)


    def run_tasks(self, task_control):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param task_control: L{TaskControl}
        """
        for task in task_control.get_next_task():
            if self._stop_running:
                break
            if not self.select_task(task):
                continue
            catched_excp = self.execute_task(task)
            self.process_task_result(task, catched_excp)


    def teardown(self):
        """run teardown from all tasks"""
        for task in self.teardown_list:
            catched = task.execute_teardown(sys.stdout, sys.stderr,
                                            self.verbosity)
            if catched:
                msg = "ERROR: task '%s' teardown action" % task.name
                error = SetupError(msg, catched)
                self.reporter.cleanup_error(error)


    def finish(self):
        """finish running tasks"""
        # flush update dependencies
        self.dependencyManager.close()

        # clean setup objects
        error = self.setupManager.cleanup()
        if error:
            self.reporter.cleanup_error(error)

        # new style teardown
        self.teardown()

        # report final results
        self.reporter.complete_run()
        return self.final_result
