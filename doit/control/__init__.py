"""Task control and execution ordering.

This package manages task dependencies, selection, and dispatch order.

Main classes:
    TaskControl: Manages task dependencies and selection
    TaskDispatcher: Dispatches tasks in execution order
    ExecNode: Execution state for a single task

Type-safe enums (new):
    TaskRunStatus: Enum of task execution states
    DispatcherSignal: Enum of generator protocol signals

Registries (new):
    TaskRegistry: Task name → Task mapping
    TargetRegistry: Target file → task name mapping
    ExecNodeRegistry: Task name → ExecNode mapping
"""

# Re-export existing classes for backward compatibility
from ._control import (
    TaskControl,
    TaskDispatcher,
    ExecNode,
    no_none,
)

# Task selection
from .selector import TaskSelector, RegexGroup

# New type-safe additions
from .types import TaskRunStatus, DispatcherSignal
from .registries import TaskRegistry, TargetRegistry, ExecNodeRegistry

__all__ = [
    # Main classes (backward compat)
    'TaskControl',
    'TaskDispatcher',
    'ExecNode',
    'no_none',

    # Selection
    'TaskSelector',
    'RegexGroup',

    # Types (new)
    'TaskRunStatus',
    'DispatcherSignal',

    # Registries (new)
    'TaskRegistry',
    'TargetRegistry',
    'ExecNodeRegistry',
]
