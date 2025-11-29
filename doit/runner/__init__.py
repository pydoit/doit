"""Task runner package.

This package provides task runners for executing doit tasks:

Main classes:
    Runner: Sequential task runner
    MThreadRunner: Parallel runner using threads
    TaskExecutor: Low-level task execution logic

Types:
    ResultCode: Enum for execution results (SUCCESS/FAILURE/ERROR)
"""

# Types
from .types import ResultCode

# Callbacks
from .callbacks import ReporterCallbacks

# Executor
from .executor import TaskExecutor

# Runners
from .base import Runner
from .parallel import MThreadRunner

__all__ = [
    # Result codes
    'ResultCode',

    # Callbacks
    'ReporterCallbacks',

    # Executor
    'TaskExecutor',

    # Runners
    'Runner',
    'MThreadRunner',
]
