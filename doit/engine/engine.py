"""Main DoitEngine class for programmatic task execution.

This module provides the primary interface for running doit tasks
programmatically with full control over execution.
"""

from ..control import TaskControl
from ..dependency import Dependency, DbmDB, ProcessingStateStore
from ..task import Task, dict_to_task, Stream
from .iterator import TaskIterator


def create_task_iterator(
    tasks,
    *,
    store=None,
    db_path='.doit.db',
    selected=None,
    always_execute=False,
    verbosity=0,
):
    """Create a TaskIterator for programmatic task execution.

    This is a lower-level factory function. Most users should use
    DoitEngine instead.

    Args:
        tasks: List of Task objects or task dicts
        store: StateStore instance (e.g., MemoryStore()) for custom storage.
            If None, uses file-based storage at db_path.
        db_path: Path to database file (default: '.doit.db').
            Ignored if store is provided.
        selected: List of task names to run (None = all)
        always_execute: Force execution even if up-to-date
        verbosity: Output verbosity (0, 1, or 2)

    Returns:
        TaskIterator instance
    """
    # Convert dicts to Task objects
    task_list = []
    for t in tasks:
        if isinstance(t, dict):
            task_list.append(dict_to_task(t))
        elif isinstance(t, Task):
            task_list.append(t)
        else:
            raise TypeError(f"Expected Task or dict, got {type(t)}")

    # Create task control
    task_control = TaskControl(task_list)
    task_control.process(selected)

    # Create dependency manager
    if store is not None:
        if isinstance(store, ProcessingStateStore):
            dep_manager = Dependency(store)
        elif isinstance(store, Dependency):
            dep_manager = store
        else:
            raise TypeError(
                f"store must be a StateStore or Dependency, got {type(store)}"
            )
    else:
        dep_manager = Dependency(DbmDB, db_path)

    stream = Stream(verbosity)

    return TaskIterator(
        task_control=task_control,
        dep_manager=dep_manager,
        stream=stream,
        always_execute=always_execute,
    )


class DoitEngine:
    """Engine for programmatic doit execution.

    Can be used as a context manager (recommended) or with explicit finish().

    Example (context manager):
        from doit import DoitEngine

        tasks = [
            {'name': 'build', 'actions': ['make']},
            {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
        ]

        with DoitEngine(tasks) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

    Example (explicit finish):
        engine = DoitEngine(tasks)
        try:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
        finally:
            engine.finish()

    For in-memory execution (no persistence):
        from doit.state import MemoryStore

        with DoitEngine(tasks, store=MemoryStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
    """

    def __init__(
        self,
        tasks,
        *,
        store=None,
        db_path='.doit.db',
        selected=None,
        always_execute=False,
        verbosity=0,
    ):
        """Initialize DoitEngine and create the task iterator.

        @param tasks: List of Task objects or task dicts
        @param store: StateStore instance for custom storage (e.g., MemoryStore()).
            If None, uses file-based storage at db_path.
        @param db_path: Path to database file (default: '.doit.db').
            Ignored if store is provided.
        @param selected: List of task names to run (None = all)
        @param always_execute: Force execution even if up-to-date
        @param verbosity: Output verbosity (0, 1, or 2)
        """
        self._iterator = create_task_iterator(
            tasks,
            store=store,
            db_path=db_path,
            selected=selected,
            always_execute=always_execute,
            verbosity=verbosity,
        )

    def __iter__(self):
        """Iterate over tasks. Delegates to the underlying TaskIterator."""
        return self._iterator

    def __next__(self):
        """Get next task. Delegates to the underlying TaskIterator."""
        return next(self._iterator)

    def finish(self):
        """Run teardowns and close the dependency database.

        This must be called when you're done iterating, unless you're using
        the context manager (which calls it automatically).
        """
        self._iterator.finish()

    def add_task(self, task):
        """Add a new task dynamically.

        @param task: Task instance or dict with task definition
        @return: The added Task instance
        """
        return self._iterator.add_task(task)

    def add_tasks(self, tasks):
        """Add multiple tasks dynamically.

        @param tasks: List of Task instances or dicts
        @return: List of added Task instances
        """
        return self._iterator.add_tasks(tasks)

    @property
    def tasks(self):
        """Access all tasks dict."""
        return self._iterator.tasks

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False  # Don't suppress exceptions
