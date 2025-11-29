"""Task wrapper for programmatic execution control.

This module provides TaskWrapper, a user-friendly interface for controlling
individual task execution in programmatic mode. It wraps a task node and
executor, providing methods for executing and submitting task results.
"""

from ..control.types import TaskRunStatus
from .callbacks import NullCallbacks
from .status import TaskStatus


class TaskWrapper:
    """User-friendly wrapper for controlling task execution.

    Provides three levels of control:
    - execute_and_submit(): Run and save results (convenience)
    - execute() + submit(): Run, then save separately
    - Manual: Access raw actions, run yourself, call submit()

    Core attributes:
        name (str): Task name
        task (Task): Underlying Task object
        actions (list): Raw action objects

    Task definition properties (delegated to underlying task):
        file_dep (set): File dependencies
        task_dep (list): Task dependencies
        targets (list): Target files
        uptodate (list): Up-to-date conditions
        calc_dep (set): Calculated dependencies
        setup_tasks (list): Setup task names
        teardown (list): Teardown actions
        doc (str|None): Task documentation
        meta (dict|None): User/plugin metadata
        getargs (dict): Values from other tasks
        verbosity (int|None): Task verbosity level
        subtask_of (str|None): Parent task name if subtask
        has_subtask (bool): Whether task has subtasks

    Execution state properties:
        should_run (bool): Whether task needs execution
        skip_reason (str|None): Why task was skipped, if applicable
        status (str): Current TaskStatus
        result: Execution result after execute()
        values (dict): Task output values after execution
        executed (bool): Whether execute() has been called
        submitted (bool): Whether submit() has been called
    """

    def __init__(self, node, executor, tasks_dict, teardown_list=None, callbacks=None):
        """Initialize TaskWrapper.

        @param node: ExecNode from TaskDispatcher
        @param executor: TaskExecutor instance
        @param tasks_dict: dict of all tasks (for getargs resolution)
        @param teardown_list: optional list to append tasks with teardowns
        @param callbacks: optional ExecutionCallbacks for lifecycle notifications
        """
        self._node = node
        self._executor = executor
        self._tasks_dict = tasks_dict
        self._teardown_list = teardown_list
        self._callbacks = callbacks if callbacks is not None else NullCallbacks()
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

    # --- Task definition properties (delegated to underlying task) ---

    @property
    def file_dep(self):
        """File dependencies (set of absolute paths)."""
        return self._node.task.file_dep

    @property
    def task_dep(self):
        """Task dependencies (list of task names)."""
        return self._node.task.task_dep

    @property
    def targets(self):
        """Target files (list of paths)."""
        return self._node.task.targets

    @property
    def uptodate(self):
        """Up-to-date conditions (list)."""
        return self._node.task.uptodate

    @property
    def calc_dep(self):
        """Calculated dependencies (set of task names)."""
        return self._node.task.calc_dep

    @property
    def setup_tasks(self):
        """Setup task names (list)."""
        return self._node.task.setup_tasks

    @property
    def teardown(self):
        """Teardown actions (list)."""
        return self._node.task.teardown

    @property
    def doc(self):
        """Task documentation string (or None)."""
        return self._node.task.doc

    @property
    def meta(self):
        """User/plugin metadata dict (or None)."""
        return self._node.task.meta

    @property
    def getargs(self):
        """Dict of values to get from other tasks."""
        return self._node.task.getargs

    @property
    def verbosity(self):
        """Task verbosity level (0, 1, 2, or None for default)."""
        return self._node.task.verbosity

    @property
    def subtask_of(self):
        """Parent task name if this is a subtask (or None)."""
        return self._node.task.subtask_of

    @property
    def has_subtask(self):
        """True if this task has subtasks."""
        return self._node.task.has_subtask

    # --- Execution state properties ---

    @property
    def should_run(self):
        """Whether this task needs to be executed."""
        return self._node.run_status == TaskRunStatus.RUN

    @property
    def is_setup_task(self):
        """True if this task is being run as a setup task for another task."""
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
        if self._node.run_status in (TaskRunStatus.UPTODATE, TaskRunStatus.IGNORE):
            return self._node.run_status.value
        return None

    @property
    def status(self):
        """Current task status (TaskStatus constant)."""
        if self._submitted:
            if self._execution_result is None:
                return TaskStatus.SUCCESS
            return TaskStatus.FAILURE
        if self._executed:
            return TaskStatus.RUNNING  # executed but not submitted
        rs = self._node.run_status
        if rs is None or rs == TaskRunStatus.PENDING:
            return TaskStatus.PENDING
        if rs == TaskRunStatus.UPTODATE:
            return TaskStatus.SKIPPED_UPTODATE
        if rs == TaskRunStatus.IGNORE:
            return TaskStatus.SKIPPED_IGNORED
        if rs == TaskRunStatus.RUN:
            return TaskStatus.READY
        if rs == TaskRunStatus.FAILURE:
            return TaskStatus.FAILURE
        if rs == TaskRunStatus.ERROR:
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
                f"Task '{self.name}' should not run "
                f"(status: {self._node.run_status})"
            )

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

        # Notify callback before execution
        self._callbacks.on_execute(self._node.task)

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
                self._node.run_status = TaskRunStatus.SUCCESSFUL
                self._callbacks.on_success(self._node.task)
                return True
            else:
                self._node.run_status = TaskRunStatus.FAILURE
                self._execution_result = error
                self._callbacks.on_failure(self._node.task, error)
                return False
        else:
            # Failure path
            self._executor.save_task_result(
                self._node.task, self._execution_result)
            self._node.run_status = TaskRunStatus.FAILURE
            self._callbacks.on_failure(self._node.task, self._execution_result)
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
