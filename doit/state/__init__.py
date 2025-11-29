"""Task state storage backends.

This package provides storage backends for task execution state,
including file dependencies, checksums, and task results.

Core classes (small, focused components):
    StateStore: Abstract base class for storage backends
    MemoryStore: In-memory storage for testing/ephemeral use
    DbmStore: DBM-based file storage
    TaskState: Task state persistence (values, results, ignore status)
    UpToDateChecker: Check if task needs to run

High-level interface:
    DependencyManager: Facade combining TaskState + UpToDateChecker

For simple usage, import from doit.state:
    from doit.state import MemoryStore

    with DoitEngine(tasks, store=MemoryStore()) as engine:
        ...
"""

# Re-export from dependency.py with cleaner names
from ..dependency import (
    # Storage backends
    ProcessingStateStore as StateStore,
    InMemoryStateStore as MemoryStore,
    DbmDB as DbmStore,
    JsonDB as JsonStore,
    SqliteDB as SqliteStore,

    # Checkers
    MD5Checker,
    TimestampChecker,

    # Core components (new focused classes)
    TaskState,
    UpToDateChecker,

    # Manager (facade for backward compatibility)
    Dependency as DependencyManager,
)

__all__ = [
    # Storage backends
    'StateStore',
    'MemoryStore',
    'DbmStore',
    'JsonStore',
    'SqliteStore',

    # Checkers
    'MD5Checker',
    'TimestampChecker',

    # Core components
    'TaskState',
    'UpToDateChecker',

    # Manager
    'DependencyManager',
]
