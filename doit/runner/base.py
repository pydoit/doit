"""Base runner for sequential task execution.

Runner orchestrates task execution via TaskIterator, handling:
- Reporter-based output
- Error handling and continuation policies
- Teardown/cleanup

Uses TaskIterator for task iteration and status checking,
ReporterCallbacks to bridge Reporter to ExecutionCallbacks,
and TaskExecutor for pure execution logic.
"""

from ..exceptions import InvalidTask, UnmetDependency
from ..task import Stream
from ..engine.iterator import TaskIterator
from .callbacks import ReporterCallbacks
from .types import ResultCode


class Runner:
    """Task runner for sequential execution.

    Uses TaskIterator internally for task iteration and status checking.
    The ReporterCallbacks adapter bridges Reporter to the ExecutionCallbacks
    protocol, enabling consistent lifecycle notifications.

    Orchestration flow:
    - run_all() is the entry point
    - Creates TaskIterator with ReporterCallbacks
    - Iterates through tasks, executing those that should_run
    - Handles errors and continuation policy via ReporterCallbacks
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

        # Runner state
        self.final_result = ResultCode.SUCCESS

    def run_tasks(self, iterator, callbacks):
        """Run tasks using TaskIterator.

        @param iterator: TaskIterator instance
        @param callbacks: ReporterCallbacks for lifecycle notifications
        """
        for wrapper in iterator:
            # Check if we should stop (set by ReporterCallbacks on error)
            if callbacks.stop_running:
                break

            # Handle unmet dependencies
            if wrapper._node.bad_deps:
                bad_str = " ".join(n.task.name for n in wrapper._node.bad_deps)
                error = UnmetDependency(bad_str)
                wrapper._executed = True  # Mark as executed to allow submit
                wrapper.submit(error)
                continue

            # Skip tasks that don't need to run
            if not wrapper.should_run:
                continue

            # Execute and submit result
            wrapper.execute_and_submit()

    def run_all(self, task_control):
        """Entry point to run tasks.

        @param task_control: TaskControl with processed tasks
        @return: ResultCode indicating success/failure/error
        """
        # Create callbacks adapter
        callbacks = ReporterCallbacks(
            reporter=self.reporter,
            dep_manager=self.dep_manager,
            continue_=self.continue_,
        )

        # Create TaskIterator
        iterator = TaskIterator(
            task_control=task_control,
            dep_manager=self.dep_manager,
            stream=self.stream,
            always_execute=self.always_execute,
            callbacks=callbacks,
        )

        try:
            # Initialize reporter
            if hasattr(self.reporter, 'initialize'):
                self.reporter.initialize(
                    iterator.tasks,
                    task_control.selected_tasks,
                )

            # Run tasks
            self.run_tasks(iterator, callbacks)

        except InvalidTask as exception:
            self.reporter.runtime_error(str(exception))
            callbacks.final_result = ResultCode.ERROR

        finally:
            # Finish: run teardowns, close DB
            iterator.finish()
            # Report completion
            self.reporter.complete_run()

        return callbacks.final_result
