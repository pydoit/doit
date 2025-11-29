"""Type-safe enums for task runner.

Provides typed constants for execution results used throughout the runner module.
"""

from enum import IntEnum


class ResultCode(IntEnum):
    """Execution result codes for task runs.

    Used by Runner classes to indicate overall execution outcome.
    IntEnum allows backward-compatible integer comparisons (e.g., if result == 0).
    """
    SUCCESS = 0   # All tasks completed successfully
    FAILURE = 1   # One or more tasks failed
    ERROR = 2     # Internal error (not a task failure)


# Backward compatibility aliases at module level
SUCCESS = ResultCode.SUCCESS
FAILURE = ResultCode.FAILURE
ERROR = ResultCode.ERROR
