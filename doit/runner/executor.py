"""Task execution logic.

TaskExecutor handles the pure execution of individual tasks:
- Checking up-to-date status
- Preparing task arguments (getargs)
- Executing task actions
- Saving results

This is separate from orchestration (Runner) and reporting concerns.
"""

from ..control.types import TaskRunStatus
from ..exceptions import DependencyError
from ..task import Stream


class TaskExecutor:
    """Handles individual task execution, separated from orchestration and reporting.

    This class encapsulates the pure execution logic:
    - Checking if a task should run (up-to-date status)
    - Preparing task arguments (getargs)
    - Executing task actions
    - Saving task results to the dependency manager

    It does NOT handle reporting or orchestration decisions (like continue on failure).
    """

    def __init__(self, dep_manager, stream=None, always_execute=False):
        """
        @param dep_manager: DependencyBase for checking/saving task state
        @param stream: (task.Stream) output verbosity control
        @param always_execute: (bool) force execution even if up-to-date
        """
        self.dep_manager = dep_manager
        self.stream = stream if stream else Stream(0)
        self.always_execute = always_execute

    def get_task_status(self, task, tasks_dict):
        """Check if task is up-to-date.

        Returns:
            tuple: (status: TaskRunStatus, error: BaseFail|None)
                status is one of: RUN, UPTODATE, ERROR
                error is set only when status is ERROR
        """
        res = self.dep_manager.get_status(task, tasks_dict)
        if res.status == 'error':
            msg = "ERROR: Task '{}' checking dependencies: {}".format(
                task.name, res.get_error_message())
            return (TaskRunStatus.ERROR, DependencyError(msg))

        if self.always_execute:
            return (TaskRunStatus.RUN, None)

        # Map dependency status string to TaskRunStatus enum
        if res.status == 'up-to-date':
            return (TaskRunStatus.UPTODATE, None)
        return (TaskRunStatus.RUN, None)

    def prepare_task_args(self, task, tasks_dict):
        """Prepare task options including getargs from other tasks.

        Returns:
            BaseFail|None: Error if argument preparation failed, None on success
        """
        task.init_options()

        def get_value(task_id, key_name):
            """get single value or dict from task's saved values"""
            if key_name is None:
                return self.dep_manager.get_values(task_id)
            return self.dep_manager.get_value(task_id, key_name)

        try:
            for arg, value in task.getargs.items():
                task_id, key_name = value

                if tasks_dict[task_id].has_subtask:
                    # if a group task, pass values from all sub-tasks
                    arg_value = {}
                    base_len = len(task_id) + 1  # length of base name string
                    for sub_id in tasks_dict[task_id].task_dep:
                        name = sub_id[base_len:]
                        arg_value[name] = get_value(sub_id, key_name)
                else:
                    arg_value = get_value(task_id, key_name)
                task.options[arg] = arg_value
            return None
        except Exception as exception:
            msg = "ERROR getting value for argument\n" + str(exception)
            return DependencyError(msg)

    def execute_task(self, task):
        """Execute task's actions.

        Returns:
            BaseFail|None: Error if execution failed, None on success
        """
        return task.execute(self.stream)

    def save_task_result(self, task, base_fail):
        """Save execution result to dependency manager.

        Returns:
            tuple: (success: bool, error: BaseFail|None)
        """
        if base_fail is None:
            task.save_extra_values()
            try:
                self.dep_manager.save_success(task)
                return (True, None)
            except FileNotFoundError as exception:
                msg = (f"ERROR: Task '{task.name}' saving success: "
                       f"Dependent file '{exception.filename}' does not exist.")
                return (False, DependencyError(msg))
        else:
            self.dep_manager.remove_success(task)
            return (False, None)
