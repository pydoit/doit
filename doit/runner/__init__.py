"""Task runner package.

This package provides task runners for executing doit tasks:

Main classes:
    Runner: Sequential task runner
    MRunner: Parallel runner using multiprocessing
    MThreadRunner: Parallel runner using threads
    TaskExecutor: Low-level task execution logic

Types:
    ResultCode: Enum for execution results (SUCCESS/FAILURE/ERROR)

Job classes (for parallel execution):
    JobHold: Signal that no task is ready
    JobTask: Full task pickle for subprocess
    JobTaskPickle: Partial task data for subprocess
"""

# Types
from .types import ResultCode, SUCCESS, FAILURE, ERROR

# Executor
from .executor import TaskExecutor

# Runners
from .base import Runner
from .parallel import (
    MRunner,
    MThreadRunner,
    MReporter,
    JobHold,
    JobTask,
    JobTaskPickle,
)

__all__ = [
    # Result codes
    'ResultCode',
    'SUCCESS',
    'FAILURE',
    'ERROR',

    # Executor
    'TaskExecutor',

    # Runners
    'Runner',
    'MRunner',
    'MThreadRunner',

    # Internal (for parallel execution)
    'MReporter',
    'JobHold',
    'JobTask',
    'JobTaskPickle',
]
