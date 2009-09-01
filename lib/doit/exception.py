"""Task exceptions"""

class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass

class TaskFailed(Exception):
    """Task execution was not successful."""
    pass

class TaskError(Exception):
    """Error while trying to execute task."""
    pass

