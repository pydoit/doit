"""Programmatic task execution engine.

This package provides the primary interface for running doit tasks
programmatically with full control over execution.

Main classes:
    DoitEngine: Context manager for task execution (recommended entry point)
    TaskWrapper: Wrapper providing control over individual task execution
    TaskStatus: Constants for task execution states
    ExecutionCallbacks: Protocol for lifecycle callbacks (used by Runner)
    NullCallbacks: Default no-op callback implementation

Example usage:
    from doit.engine import DoitEngine

    tasks = [
        {'name': 'build', 'actions': ['make']},
        {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
    ]

    with DoitEngine(tasks) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()
"""

from .callbacks import ExecutionCallbacks, NullCallbacks
from .engine import DoitEngine, create_task_iterator
from .wrapper import TaskWrapper
from .status import TaskStatus

__all__ = [
    'DoitEngine',
    'create_task_iterator',
    'TaskWrapper',
    'TaskStatus',
    'ExecutionCallbacks',
    'NullCallbacks',
]
