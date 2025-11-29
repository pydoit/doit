"""Reporter adapter for ExecutionCallbacks protocol.

This module provides ReporterCallbacks, which adapts a doit Reporter object
to the ExecutionCallbacks protocol. This allows Runner to use TaskIterator
internally while maintaining reporter-based output.
"""

from ..exceptions import TaskFailed
from .types import ResultCode


class ReporterCallbacks:
    """Adapts a Reporter to the ExecutionCallbacks protocol.

    This class bridges the Reporter interface (used by CLI) with the
    ExecutionCallbacks protocol (used by TaskIterator). It also tracks
    execution state like final_result and stop_running.

    Attributes:
        reporter: The underlying Reporter instance
        dep_manager: Dependency manager for remove_success on failure
        continue_: Whether to continue execution after task failure
        final_result: Final execution result (SUCCESS/FAILURE/ERROR)
        stop_running: Flag to signal execution should stop
    """

    def __init__(self, reporter, dep_manager, continue_=False):
        """Initialize ReporterCallbacks.

        @param reporter: Reporter instance for output
        @param dep_manager: Dependency manager (for remove_success on failure)
        @param continue_: Whether to continue on task failure (default: False)
        """
        self.reporter = reporter
        self.dep_manager = dep_manager
        self.continue_ = continue_
        self.final_result = ResultCode.SUCCESS
        self.stop_running = False

    def on_status_check(self, task):
        """Called when checking task status."""
        self.reporter.get_status(task)

    def on_skip_uptodate(self, task):
        """Called when task is skipped because it's up-to-date."""
        self.reporter.skip_uptodate(task)

    def on_skip_ignored(self, task):
        """Called when task is skipped because it's ignored."""
        self.reporter.skip_ignore(task)

    def on_execute(self, task):
        """Called immediately before task execution."""
        self.reporter.execute_task(task)

    def on_success(self, task):
        """Called after successful task execution."""
        self.reporter.add_success(task)

    def on_failure(self, task, error):
        """Called after failed task execution.

        Updates final_result and stop_running based on error type.
        """
        # Remove any saved success state for this task
        self.dep_manager.remove_success(task)

        # Report the failure
        self.reporter.add_failure(task, error)

        # Update final result: ERROR for non-TaskFailed, FAILURE for TaskFailed
        if isinstance(error, TaskFailed) and self.final_result != ResultCode.ERROR:
            self.final_result = ResultCode.FAILURE
        else:
            self.final_result = ResultCode.ERROR

        # Stop running unless continue_ is set
        if not self.continue_:
            self.stop_running = True

    def on_teardown(self, task):
        """Called before running task teardown."""
        self.reporter.teardown_task(task)
