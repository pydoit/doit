"""Type-safe enums and constants for task control.

Replaces magic strings used throughout control.py with typed enums
that provide IDE support and prevent typo-related bugs.
"""

from enum import Enum


class TaskRunStatus(Enum):
    """Status of a task's execution decision.

    Used by ExecNode.run_status to track whether a task should run.

    Status flow:
        PENDING -> RUN/UPTODATE/IGNORE/ERROR/FAILURE
        RUN -> SUCCESSFUL/FAILURE (after execution)
        SUCCESSFUL/FAILURE -> DONE (internal, for dispatcher)
    """
    PENDING = None           # Not yet determined
    RUN = 'run'              # Task needs to execute
    UPTODATE = 'up-to-date'  # Task is up-to-date, skip
    IGNORE = 'ignore'        # Task marked as ignored
    ERROR = 'error'          # Error checking status (e.g., missing file_dep)
    FAILURE = 'failure'      # Task or dependency failed
    SUCCESSFUL = 'successful'  # Task executed successfully
    DONE = 'done'            # Task completed (used internally by dispatcher)


class DispatcherSignal(Enum):
    """Signals yielded by dispatcher generators.

    The dispatcher uses a generator protocol where yields can be:
    - An ExecNode (to process a dependency)
    - A Task (ready to execute)
    - A signal (to coordinate state)
    """
    WAIT = 'wait'                    # Wait for dependencies to complete
    HOLD_ON = 'hold on'              # No tasks ready, caller should wait
    RESET = 'reset generator'        # Task was regenerated, restart processing
