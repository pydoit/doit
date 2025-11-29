"""Task state storage backends.

This package provides storage backends for task execution state,
including file dependencies, checksums, and task results.

Main classes:
    StateStore: Abstract base class for storage backends (alias for ProcessingStateStore)
    MemoryStore: In-memory storage for testing/ephemeral use (alias for InMemoryStateStore)
    DbmStore: DBM-based file storage (alias for DbmDB)
    DependencyManager: Manager combining storage with change checking (alias for Dependency)

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

    # Manager
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

    # Manager
    'DependencyManager',
]
