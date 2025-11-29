"""Task state storage backends.

This package provides storage backends for task execution state,
including file dependencies, checksums, and task results.

Import from doit.dependency for storage backends:
    from doit.dependency import DbmDB, JsonDB, SqliteDB, InMemoryStateStore
    from doit.dependency import Dependency  # facade manager

This package is reserved for future state-related components.
"""
