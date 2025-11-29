"""Thread-based parallel task execution runner.

Provides MThreadRunner for parallel task execution using threads.
Uses the same TaskIterator-based approach as the sequential Runner,
with ThreadPoolExecutor for parallel execution.
"""

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from ..task import Stream
from ..engine.iterator import TaskIterator
from .callbacks import ReporterCallbacks
from .base import Runner


class MThreadRunner(Runner):
    """Thread-based parallel task runner.

    Uses TaskIterator with get_ready_tasks() and notify_completed()
    for thread-safe parallel execution.
    """

    def __init__(self, dep_manager, reporter,
                 continue_=False, always_execute=False,
                 stream=None, num_process=1):
        """Initialize MThreadRunner.

        @param dep_manager: DependencyBase
        @param reporter: reporter object to be used
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param stream: (task.Stream) global verbosity
        @param num_process: (int) number of worker threads
        """
        Runner.__init__(self, dep_manager, reporter, continue_=continue_,
                        always_execute=always_execute, stream=stream)
        self.num_process = num_process

    @staticmethod
    def available():
        """Check if threading is available (always True)."""
        return True

    def run_tasks(self, iterator, callbacks):
        """Run tasks in parallel using threads.

        @param iterator: TaskIterator instance
        @param callbacks: ReporterCallbacks for lifecycle notifications
        """
        from ..exceptions import UnmetDependency

        with ThreadPoolExecutor(max_workers=self.num_process) as executor:
            futures = {}  # future -> wrapper

            while iterator.has_pending_tasks:
                # Check if we should stop
                if callbacks.stop_running:
                    # Cancel pending futures
                    for future in futures:
                        future.cancel()
                    break

                # Get all ready tasks and submit them
                for wrapper in iterator.get_ready_tasks():
                    # Handle unmet dependencies
                    if wrapper._node.bad_deps:
                        bad_str = " ".join(
                            n.task.name for n in wrapper._node.bad_deps)
                        error = UnmetDependency(bad_str)
                        wrapper._executed = True
                        wrapper.submit(error)
                        iterator.notify_completed(wrapper)
                        continue

                    # Skip tasks that don't need to run
                    if not wrapper.should_run:
                        # For skipped tasks, mark as submitted so we can notify
                        wrapper._submitted = True
                        iterator.notify_completed(wrapper)
                        continue

                    # Submit task for execution
                    future = executor.submit(wrapper.execute)
                    futures[future] = wrapper

                # Wait for at least one task to complete
                if futures:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)

                    for future in done:
                        wrapper = futures.pop(future)
                        try:
                            result = future.result()
                            wrapper.submit(result)
                        except SystemExit:
                            # Re-raise SystemExit to propagate it
                            raise
                        except Exception as e:
                            # Submit the exception as a failure
                            from ..exceptions import TaskError
                            wrapper._executed = True
                            wrapper.submit(TaskError(str(e)))
                        iterator.notify_completed(wrapper)

            # Wait for any remaining futures
            if futures:
                done, _ = wait(futures)
                for future in done:
                    wrapper = futures.pop(future)
                    try:
                        result = future.result()
                        wrapper.submit(result)
                    except SystemExit:
                        raise
                    except Exception as e:
                        from ..exceptions import TaskError
                        wrapper._executed = True
                        wrapper.submit(TaskError(str(e)))
                    iterator.notify_completed(wrapper)
