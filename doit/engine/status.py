"""Task execution status constants."""


class TaskStatus:
    """Task execution status.

    Possible values:
        PENDING: Task not yet processed
        READY: Ready to execute (dependencies satisfied)
        RUNNING: Executed but not yet submitted
        SUCCESS: Completed successfully
        FAILURE: Task failed
        SKIPPED_UPTODATE: Skipped because up-to-date
        SKIPPED_IGNORED: Skipped because ignored
        ERROR: Error checking dependencies
    """
    PENDING = 'pending'
    READY = 'ready'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'
    SKIPPED_UPTODATE = 'up-to-date'
    SKIPPED_IGNORED = 'ignored'
    ERROR = 'error'
