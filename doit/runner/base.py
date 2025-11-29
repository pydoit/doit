"""Base runner for sequential task execution.

Runner orchestrates task execution, handling:
- Task selection (which tasks to run)
- Execution ordering (respecting dependencies)
- Error handling and continuation policies
- Teardown/cleanup
- Reporting

Uses TaskExecutor for pure execution logic.
"""

from ..exceptions import InvalidTask, BaseFail, TaskFailed, SetupError, UnmetDependency
from ..task import Stream
from .executor import TaskExecutor
from .types import ResultCode, SUCCESS, FAILURE, ERROR


class Runner:
    """Task runner for sequential execution.

    Orchestrates task execution:
    - run_all() is the entry point
    - run_tasks() iterates through tasks from dispatcher
    - select_task() determines if a task should run
    - execute_task() runs the task
    - process_task_result() handles success/failure

    Uses TaskExecutor for pure execution logic (status checking, arg prep,
    execution, result saving). Runner handles orchestration and reporting.
    """

    def __init__(self, dep_manager, reporter, continue_=False,
                 always_execute=False, stream=None):
        """
        @param dep_manager: DependencyBase
        @param reporter: reporter object to be used
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param stream: (task.Stream) global verbosity
        """
        self.dep_manager = dep_manager
        self.reporter = reporter
        self.continue_ = continue_
        self.always_execute = always_execute
        self.stream = stream if stream else Stream(0)

        # Create executor for pure execution logic
        self._executor = TaskExecutor(dep_manager, self.stream, always_execute)

        self.teardown_list = []  # list of tasks to be teardown
        self.final_result = SUCCESS  # until something fails
        self._stop_running = False

    def _handle_task_error(self, node, base_fail):
        """Handle all task failures/errors.

        Called whenever there is an error before executing a task or
        its execution is not successful.
        """
        if not isinstance(base_fail, BaseFail):
            raise TypeError(f"Expected BaseFail, got {type(base_fail)}")

        node.run_status = "failure"
        self.dep_manager.remove_success(node.task)
        self.reporter.add_failure(node.task, base_fail)

        # only return FAILURE if no errors happened.
        if isinstance(base_fail, TaskFailed) and self.final_result != ERROR:
            self.final_result = FAILURE
        else:
            self.final_result = ERROR

        if not self.continue_:
            self._stop_running = True

    def _get_task_args(self, task, tasks_dict):
        """Get values from other tasks - delegates to executor."""
        error = self._executor.prepare_task_args(task, tasks_dict)
        if error:
            raise Exception(str(error))

    def select_task(self, node, tasks_dict):
        """Determine if task should be executed.

        Returns bool indicating task should be executed.
        Side-effect: sets task.options

        Tasks should be executed if they are not up-to-date.

        Tasks that contains setup-tasks must be selected twice,
        so it gives chance for dependency tasks to be executed after
        checking it is not up-to-date.
        """
        task = node.task

        # if run_status is not None, it was already calculated
        if node.run_status is None:

            self.reporter.get_status(task)

            # overwrite with effective verbosity
            task.overwrite_verbosity(self.stream)

            # check if task should be ignored (user controlled)
            if node.ignored_deps or self.dep_manager.status_is_ignore(task):
                node.run_status = 'ignore'
                self.reporter.skip_ignore(task)
                return False

            # check task_deps
            if node.bad_deps:
                bad_str = " ".join(n.task.name for n in node.bad_deps)
                self._handle_task_error(node, UnmetDependency(bad_str))
                return False

            # check if task is up-to-date using executor
            status, error = self._executor.get_task_status(task, tasks_dict)
            if error:
                self._handle_task_error(node, error)
                return False

            node.run_status = status

            # if task is up-to-date skip it
            if node.run_status == 'up-to-date':
                self.reporter.skip_uptodate(task)
                task.values = self.dep_manager.get_values(task.name)
                return False

            if task.setup_tasks:
                # dont execute now, execute setup first...
                return False
        else:
            # sanity checks - task must be in 'run' status with setup_tasks
            if node.run_status != 'run':
                raise RuntimeError(
                    f"Task {task.name} has unexpected status: {node.run_status}"
                )
            if not task.setup_tasks:
                raise RuntimeError(
                    f"Task {task.name} selected twice but has no setup_tasks"
                )

        # Prepare task args using executor
        error = self._executor.prepare_task_args(task, tasks_dict)
        if error:
            self._handle_task_error(node, error)
            return False

        return True

    def execute_task(self, task):
        """Execute task's actions."""
        # register cleanup/teardown
        if task.teardown:
            self.teardown_list.append(task)

        # finally execute it!
        self.reporter.execute_task(task)
        return self._executor.execute_task(task)

    def process_task_result(self, node, base_fail):
        """Handle task execution result."""
        task = node.task
        success, save_error = self._executor.save_task_result(task, base_fail)

        if success:
            node.run_status = "successful"
            self.reporter.add_success(task)
        elif save_error:
            # save_error means we had a FileNotFoundError during save
            self._handle_task_error(node, save_error)
        elif base_fail:
            # Original execution error
            self._handle_task_error(node, base_fail)

    def run_tasks(self, task_dispatcher):
        """Run/execute the tasks.

        Checks file dependencies to decide if task should be executed
        and saves info on successful runs.
        Also deals with output to stdout/stderr.

        @param task_dispatcher: TaskDispatcher
        """
        node = None
        while True:
            if self._stop_running:
                break

            try:
                node = task_dispatcher.generator.send(node)
            except StopIteration:
                break

            if not self.select_task(node, task_dispatcher.tasks):
                continue

            base_fail = self.execute_task(node.task)
            self.process_task_result(node, base_fail)

    def teardown(self):
        """Run teardown from all tasks."""
        for task in reversed(self.teardown_list):
            self.reporter.teardown_task(task)
            result = task.execute_teardown(self.stream)
            if result:
                msg = "ERROR: task '%s' teardown action" % task.name
                error = SetupError(msg, result)
                self.reporter.cleanup_error(error)

    def finish(self):
        """Finish running tasks."""
        # flush update dependencies
        self.dep_manager.close()
        self.teardown()

        # report final results
        self.reporter.complete_run()
        return self.final_result

    def run_all(self, task_dispatcher):
        """Entry point to run tasks.

        @param task_dispatcher: TaskDispatcher
        @return: ResultCode indicating success/failure/error
        """
        try:
            if hasattr(self.reporter, 'initialize'):
                self.reporter.initialize(task_dispatcher.tasks,
                                         task_dispatcher.selected_tasks)
            self.run_tasks(task_dispatcher)
        except InvalidTask as exception:
            self.reporter.runtime_error(str(exception))
            self.final_result = ERROR
        finally:
            self.finish()
        return self.final_result
