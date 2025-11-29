"""Task iterator for programmatic execution.

Internal module providing the TaskIterator class which handles
the low-level iteration over tasks in dependency order.
"""

from threading import Lock

from ..task import Task, dict_to_task, Stream
from ..control.types import TaskRunStatus
from ..runner import TaskExecutor
from .callbacks import NullCallbacks
from .wrapper import TaskWrapper


class TaskIterator:
    """Generator-based task dispatcher yielding TaskWrappers.

    Provides an iterator interface over tasks, yielding TaskWrapper objects
    that give the caller control over task execution.

    This is an internal class. Users should use DoitEngine instead.

    Supports two execution modes:
    1. Sequential: Use as iterator with for-loop
    2. Concurrent: Use has_pending_tasks, get_ready_tasks, notify_completed

    Attributes:
        tasks: dict of all tasks by name
        has_pending_tasks: True if there are more tasks to process
    """

    def __init__(self, task_control, dep_manager, stream=None, always_execute=False,
                 callbacks=None):
        """Initialize TaskIterator.

        @param task_control: TaskControl instance with processed tasks
        @param dep_manager: Dependency manager for state persistence
        @param stream: (optional) Stream for verbosity control
        @param always_execute: (bool) force execution even if up-to-date
        @param callbacks: (optional) ExecutionCallbacks for lifecycle notifications
        """
        self._task_control = task_control
        self._dep_manager = dep_manager
        self._stream = stream if stream else Stream(0)
        self._dispatcher = task_control.task_dispatcher()
        self._callbacks = callbacks if callbacks is not None else NullCallbacks()

        self._executor = TaskExecutor(
            dep_manager=dep_manager,
            stream=self._stream,
            always_execute=always_execute,
        )

        self._current_wrapper = None
        self._finished = False
        self._cleaned_up = False
        self._teardown_list = []
        self._lock = Lock()  # For thread-safe concurrent execution
        self._iteration_started = False  # Track if we've started iterating
        self._pending_ready = []  # Tasks returned by notify_completed, waiting for get_ready_tasks

    @property
    def tasks(self):
        """Access all tasks dict."""
        return self._task_control.tasks

    def __iter__(self):
        return self

    def _get_next_node(self, node_to_send):
        """Get the next node from the dispatcher, handling 'hold on' and 'wait'.

        @param node_to_send: The node to send back to dispatcher (or None)
        @return: The next task node
        @raises StopIteration: When no more tasks
        """
        try:
            node = self._dispatcher.generator.send(node_to_send)
        except StopIteration:
            self._finished = True
            raise

        # Handle "hold on" and "wait" - wait for dependencies
        while node in ("hold on", "wait"):
            try:
                node = self._dispatcher.generator.send(None)
            except StopIteration:
                self._finished = True
                raise

        return node

    def __next__(self):
        if self._finished:
            raise StopIteration

        self._iteration_started = True

        # Send back the last processed node
        node_to_send = None
        if self._current_wrapper is not None:
            node_to_send = self._current_wrapper._node

        # Get next node from dispatcher
        node = self._get_next_node(node_to_send)

        # Check task status (up-to-date, should run, etc.)
        self._check_node_status(node)

        # If task should run and has setup_tasks, the dispatcher will
        # yield setup tasks when we send back this node. We need to
        # process those before yielding this task.
        # Track which tasks have had their setup processed to avoid re-processing.
        task = node.task
        if (node.run_status == TaskRunStatus.RUN and task.setup_tasks and
                not getattr(node, '_setup_processed', False)):
            # Mark that we've processed setup for this task
            node._setup_processed = True
            # Send this node back so dispatcher can yield setup tasks
            try:
                setup_result = self._dispatcher.generator.send(node)
                while True:
                    # Check what dispatcher returned
                    if setup_result == "wait":
                        # Dispatcher is telling us to wait for setup tasks
                        setup_result = self._get_next_node(None)
                    elif hasattr(setup_result, 'task'):
                        # It's an ExecNode
                        if setup_result.task.name == task.name:
                            # Got the original task back - all setup done
                            node = setup_result
                            break
                        # It's a setup task node - check status and yield it
                        self._check_node_status(setup_result)
                        self._current_wrapper = TaskWrapper(
                            node=setup_result,
                            executor=self._executor,
                            tasks_dict=self._task_control.tasks,
                            teardown_list=self._teardown_list,
                            callbacks=self._callbacks,
                        )
                        return self._current_wrapper
                    elif setup_result == task:
                        # Got the Task object back (dispatcher re-yields the task)
                        node = self._dispatcher.nodes[task.name]
                        break
                    else:
                        # Some other signal from dispatcher
                        setup_result = self._get_next_node(None)
            except StopIteration:
                self._finished = True
                raise

        # Create wrapper, passing teardown_list so wrapper can register tasks
        self._current_wrapper = TaskWrapper(
            node=node,
            executor=self._executor,
            tasks_dict=self._task_control.tasks,
            teardown_list=self._teardown_list,
            callbacks=self._callbacks,
        )

        return self._current_wrapper

    def _check_node_status(self, node):
        """Determine if task should run, is up-to-date, etc."""
        if node.run_status is not None:
            return  # Already determined

        task = node.task
        task.overwrite_verbosity(self._stream)

        # Notify callback that we're checking status
        self._callbacks.on_status_check(task)

        # Check ignored
        if node.ignored_deps or self._dep_manager.status_is_ignore(task):
            node.run_status = TaskRunStatus.IGNORE
            self._callbacks.on_skip_ignored(task)
            return

        # Check bad deps
        if node.bad_deps:
            node.run_status = TaskRunStatus.FAILURE
            return

        # Check up-to-date
        status, error = self._executor.get_task_status(
            task, self._task_control.tasks)
        if error:
            node.run_status = TaskRunStatus.ERROR
            node.status_error = error  # Store error for later access
            self._callbacks.on_failure(task, error)
            return

        node.run_status = status

        # Load cached values if up-to-date
        if node.run_status == TaskRunStatus.UPTODATE:
            task.values = self._dep_manager.get_values(task.name)
            self._callbacks.on_skip_uptodate(task)

    def add_task(self, task):
        """Add a task dynamically and inject it for execution.

        The task will be registered in the task control and scheduled
        for execution in the current iteration.

        @param task: Task instance or dict with task definition
        @return: The added Task instance
        @raise TypeError: If task is not a Task or dict
        @raise InvalidTask: If task name already exists or has invalid deps
        """
        # Convert dict to Task if needed
        if isinstance(task, dict):
            task = dict_to_task(task)
        elif not isinstance(task, Task):
            raise TypeError(f"Expected Task or dict, got {type(task)}")

        # Add to task control (validates deps and registers task)
        self._task_control.add_task(task)

        # Inject into dispatcher to be yielded
        self._dispatcher.inject_task(task.name)

        return task

    def add_tasks(self, tasks):
        """Add multiple tasks dynamically.

        @param tasks: List of Task instances or dicts
        @return: List of added Task instances
        """
        return [self.add_task(t) for t in tasks]

    def finish(self):
        """Finalize: run teardowns and close DB.

        Call this when done iterating, or use DoitEngine context manager.
        """
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self._finished = True

        # Run teardowns in reverse order
        for task in reversed(self._teardown_list):
            self._callbacks.on_teardown(task)
            task.execute_teardown(self._stream)

        # Close dependency manager
        self._dep_manager.close()

    # --- Concurrent execution support ---

    @property
    def has_pending_tasks(self):
        """Check if there are more tasks to process.

        Returns True if there are tasks waiting to be yielded or executed.
        Use this to control the loop in concurrent execution mode.

        Example:
            while engine.has_pending_tasks:
                ready = engine.get_ready_tasks()
                # ... process ready tasks
        """
        # Check for tasks waiting to be returned via get_ready_tasks
        # This takes priority over _finished because the generator may have
        # ended but we still have tasks that haven't been returned to the user
        if self._pending_ready:
            return True
        if self._finished:
            return False
        # If iteration hasn't started yet, check if we have any selected tasks
        if not self._iteration_started:
            return bool(self._task_control.selected_tasks)
        # Check if dispatcher has ready tasks or waiting tasks
        dispatcher = self._dispatcher
        return bool(dispatcher.ready or dispatcher.waiting)

    def get_ready_tasks(self):
        """Get all currently ready tasks for concurrent execution.

        Returns a list of TaskWrapper objects for all tasks that are
        currently ready to execute (no pending dependencies).

        This is useful for threadpool execution where you want to
        dispatch multiple tasks in parallel.

        Thread-safe: Uses internal locking.

        Example with ThreadPoolExecutor:
            from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

            with DoitEngine(tasks) as engine:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {}

                    while engine.has_pending_tasks:
                        for task in engine.get_ready_tasks():
                            if task.should_run:
                                future = executor.submit(task.execute)
                                futures[future] = task

                        if futures:
                            done, _ = wait(futures, return_when=FIRST_COMPLETED)
                            for future in done:
                                task = futures.pop(future)
                                task.submit(future.result())
                                engine.notify_completed(task)

        @return: List of TaskWrapper objects ready for execution
        """
        with self._lock:
            return self._get_ready_tasks_unlocked()

    def _get_ready_tasks_unlocked(self):
        """Get ready tasks without locking (internal use)."""
        # First return any pending tasks from previous notify_completed calls
        # This must be checked before _finished because the generator may have
        # ended but we still have tasks that haven't been returned to the user
        if self._pending_ready:
            ready_wrappers = self._pending_ready
            self._pending_ready = []
            return ready_wrappers

        if self._finished:
            return []

        # Collect all ready tasks
        return self._collect_ready_tasks()

    def _get_next_ready(self):
        """Get next ready task without blocking on 'hold on'.

        @return: TaskWrapper if a task is ready, None if no ready tasks
        @raise StopIteration: If iteration is complete
        """
        self._iteration_started = True

        # Send back last processed node if needed
        node_to_send = None
        if self._current_wrapper is not None:
            node_to_send = self._current_wrapper._node

        # Get next node from dispatcher
        try:
            node = self._dispatcher.generator.send(node_to_send)
        except StopIteration:
            raise

        # If "hold on", no more ready tasks right now
        if node == "hold on":
            # Don't consume any more - we're waiting for completions
            self._current_wrapper = None
            return None

        # Check task status
        self._check_node_status(node)

        # Create wrapper
        self._current_wrapper = TaskWrapper(
            node=node,
            executor=self._executor,
            tasks_dict=self._task_control.tasks,
            teardown_list=self._teardown_list,
            callbacks=self._callbacks,
        )

        return self._current_wrapper

    def notify_completed(self, wrapper):
        """Notify that a task has completed execution.

        Call this after a task has been executed and submitted to update
        the dispatcher. This may cause dependent tasks to become ready.

        Thread-safe: Uses internal locking.

        @param wrapper: The TaskWrapper that was executed and submitted
        @return: List of TaskWrapper objects that became ready as a result
        """
        if not wrapper.submitted:
            raise RuntimeError(
                f"Task '{wrapper.name}' must be submitted before calling "
                "notify_completed. Call wrapper.submit() first."
            )

        with self._lock:
            # Update dispatcher with completed node
            self._dispatcher._update_waiting(wrapper._node)

            # Collect newly ready tasks
            newly_ready = self._collect_ready_tasks()

            # Store for next get_ready_tasks call
            self._pending_ready.extend(newly_ready)

            return newly_ready

    def _collect_ready_tasks(self):
        """Collect ready tasks from dispatcher without storing in pending_ready."""
        if self._finished:
            return []

        ready_wrappers = []

        while True:
            try:
                wrapper = self._get_next_ready()
                if wrapper is None:
                    break
                ready_wrappers.append(wrapper)
            except StopIteration:
                self._finished = True
                break

        return ready_wrappers
