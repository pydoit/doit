"""Task wrapper for programmatic execution control.

This module provides TaskWrapper, a user-friendly interface for controlling
individual task execution in programmatic mode. It wraps a task node and
executor, providing methods for executing and submitting task results.
"""

from .exceptions import BaseFail


class TaskStatus:
    """Task execution status constants."""
    PENDING = 'pending'
    READY = 'ready'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'
    SKIPPED_UPTODATE = 'up-to-date'
    SKIPPED_IGNORED = 'ignored'
    ERROR = 'error'


class TaskWrapper:
    """User-friendly wrapper for controlling task execution.

    Provides three levels of control:
    - execute_and_submit(): Run and save results (convenience)
    - execute() + submit(): Run, then save separately
    - Manual: Access raw actions, run yourself, call submit()

    Attributes:
        name (str): Task name
        task (Task): Underlying Task object
        actions (list): Raw action objects
        should_run (bool): Whether task needs execution
        skip_reason (str|None): Why task was skipped, if applicable
        status (str): Current TaskStatus
        result: Execution result after execute()
        values (dict): Task output values after execution
    """

    def __init__(self, node, executor, tasks_dict, teardown_list=None):
        """Initialize TaskWrapper.

        @param node: ExecNode from TaskDispatcher
        @param executor: TaskExecutor instance
        @param tasks_dict: dict of all tasks (for getargs resolution)
        @param teardown_list: optional list to append tasks with teardowns (for tracking)
        """
        self._node = node
        self._executor = executor
        self._tasks_dict = tasks_dict
        self._teardown_list = teardown_list
        self._executed = False
        self._submitted = False
        self._execution_result = None

    @property
    def name(self):
        """Task name."""
        return self._node.task.name

    @property
    def task(self):
        """Underlying Task object."""
        return self._node.task

    @property
    def actions(self):
        """List of task actions."""
        return self._node.task.actions

    @property
    def should_run(self):
        """Whether this task needs to be executed."""
        return self._node.run_status == 'run'

    @property
    def is_setup_task(self):
        """True if this task is being run as a setup task for another task."""
        # Check if this task is a subtask or if it's in any other task's setup_tasks
        task = self._node.task
        if task.subtask_of is not None:
            return False  # subtasks are not setup tasks
        # Check if this task name appears in any setup_tasks list
        for t in self._tasks_dict.values():
            if self.name in t.setup_tasks:
                return True
        return False

    @property
    def skip_reason(self):
        """Reason task was skipped, or None if not skipped."""
        if self._node.run_status in ('up-to-date', 'ignore'):
            return self._node.run_status
        return None

    @property
    def status(self):
        """Current task status (TaskStatus constant)."""
        if self._submitted:
            return TaskStatus.SUCCESS if self._execution_result is None else TaskStatus.FAILURE
        if self._executed:
            return TaskStatus.RUNNING  # executed but not submitted
        rs = self._node.run_status
        if rs is None:
            return TaskStatus.PENDING
        if rs == 'up-to-date':
            return TaskStatus.SKIPPED_UPTODATE
        if rs == 'ignore':
            return TaskStatus.SKIPPED_IGNORED
        if rs == 'run':
            return TaskStatus.READY
        if rs == 'failure':
            return TaskStatus.FAILURE
        if rs == 'error':
            return TaskStatus.ERROR
        return rs

    @property
    def result(self):
        """Execution result (BaseFail on failure, None on success)."""
        return self._execution_result

    @property
    def values(self):
        """Task output values (available after successful execution)."""
        return self._node.task.values

    @property
    def executed(self):
        """Whether execute() has been called."""
        return self._executed

    @property
    def submitted(self):
        """Whether submit() has been called."""
        return self._submitted

    def execute(self):
        """Execute the task's actions.

        Returns:
            BaseFail instance if failed, None if successful.

        Raises:
            RuntimeError: If task already executed or shouldn't run.
        """
        if self._executed:
            raise RuntimeError(f"Task '{self.name}' already executed")
        if not self.should_run:
            raise RuntimeError(
                f"Task '{self.name}' should not run (status: {self._node.run_status})")

        # Prepare args (getargs from other tasks)
        arg_error = self._executor.prepare_task_args(
            self._node.task, self._tasks_dict)
        if arg_error:
            self._execution_result = arg_error
            self._executed = True
            return arg_error

        # Register for teardown if this task has teardown actions
        if self._teardown_list is not None and self._node.task.teardown:
            self._teardown_list.append(self._node.task)

        self._executed = True
        self._execution_result = self._executor.execute_task(self._node.task)
        return self._execution_result

    def submit(self, result=None):
        """Submit execution results to doit's dependency tracking.

        Args:
            result: Override execution result. Use BaseFail for failure,
                    None for success. If not provided, uses result from execute().

        Returns:
            bool: True if submission was successful

        Raises:
            RuntimeError: If already submitted.
        """
        if self._submitted:
            raise RuntimeError(f"Task '{self.name}' already submitted")

        if result is not None:
            self._execution_result = result

        self._submitted = True

        if self._execution_result is None:
            # Success path
            success, error = self._executor.save_task_result(
                self._node.task, None)
            if success:
                self._node.run_status = 'successful'
                return True
            else:
                self._node.run_status = 'failure'
                self._execution_result = error
                return False
        else:
            # Failure path
            self._executor.save_task_result(
                self._node.task, self._execution_result)
            self._node.run_status = 'failure'
            return False

    def execute_and_submit(self):
        """Execute task and submit results. Convenience method.

        Returns:
            BaseFail instance if failed, None if successful.
        """
        result = self.execute()
        self.submit(result)
        return result

    def __repr__(self):
        return f"<TaskWrapper '{self.name}' status={self.status}>"
