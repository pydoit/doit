"""Programmatic interface for doit task execution.

This module provides a generator-based interface for running doit tasks
programmatically, with full control over task execution.

Main classes:
    DoitEngine: Context manager for task execution (recommended)
    TaskIterator: Lower-level iterator for task dispatching
    TaskWrapper: Wrapper providing control over individual task execution
    TaskStatus: Enum of possible task states

Factory functions:
    create_task_iterator: Create a TaskIterator from task definitions

Basic usage:

    from doit import DoitEngine

    tasks = [
        {'name': 'build', 'actions': ['make']},
        {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
    ]

    with DoitEngine(tasks) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

In-memory execution (no database persistence):

    from doit.dependency import InMemoryStateStore

    with DoitEngine(tasks, dep_manager=InMemoryStateStore()) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

Dynamic task injection:

    from doit.dependency import InMemoryStateStore

    with DoitEngine(initial_tasks, dep_manager=InMemoryStateStore()) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

            # Add new tasks based on results
            if task.name == 'discover':
                for item in task.values.get('discovered', []):
                    engine.add_task({
                        'name': f'process_{item}',
                        'actions': [process_fn],
                    })

Manual iteration (without context manager):

    from doit.dependency import InMemoryStateStore

    iterator = create_task_iterator(tasks, dep_manager=InMemoryStateStore())
    try:
        for task in iterator:
            if task.should_run:
                task.execute_and_submit()
    finally:
        iterator.finish()  # Run teardowns and close DB
"""

from .control import TaskControl
from .dependency import (
    Dependency, DbmDB, MD5Checker, TimestampChecker,
    InMemoryStateStore, ProcessingStateStore
)
from .runner import TaskExecutor
from .task import Task, dict_to_task, Stream
from .task_wrapper import TaskWrapper, TaskStatus


class TaskIterator:
    """Generator-based task dispatcher yielding TaskWrappers.

    Provides an iterator interface over tasks, yielding TaskWrapper objects
    that give the caller control over task execution.

    Usage:
        iterator = TaskIterator(task_control, dep_manager)
        for wrapper in iterator:
            if wrapper.should_run:
                wrapper.execute_and_submit()
            # Optionally add new tasks:
            # iterator.add_task(new_task_dict)
        iterator.finish()

    Attributes:
        tasks: dict of all tasks by name
    """

    def __init__(self, task_control, dep_manager, stream=None, always_execute=False):
        """Initialize TaskIterator.

        @param task_control: TaskControl instance with processed tasks
        @param dep_manager: Dependency manager for state persistence
        @param stream: (optional) Stream for verbosity control
        @param always_execute: (bool) force execution even if up-to-date
        """
        self._task_control = task_control
        self._dep_manager = dep_manager
        self._stream = stream if stream else Stream(0)
        self._dispatcher = task_control.task_dispatcher()

        self._executor = TaskExecutor(
            dep_manager=dep_manager,
            stream=self._stream,
            always_execute=always_execute,
        )

        self._current_wrapper = None
        self._finished = False
        self._cleaned_up = False
        self._teardown_list = []

    @property
    def tasks(self):
        """Access all tasks dict."""
        return self._task_control.tasks

    def __iter__(self):
        return self

    def __next__(self):
        if self._finished:
            raise StopIteration

        # Send back the last processed node
        node_to_send = None
        if self._current_wrapper is not None:
            node_to_send = self._current_wrapper._node

        # Get next node from dispatcher
        try:
            node = self._dispatcher.generator.send(node_to_send)
        except StopIteration:
            self._finished = True
            raise

        # Handle "hold on" - in single-threaded mode, this means we need to
        # continue sending back processed nodes until we get a real task
        while node == "hold on":
            try:
                node = self._dispatcher.generator.send(None)
            except StopIteration:
                self._finished = True
                raise

        # Check task status (up-to-date, should run, etc.)
        self._check_node_status(node)

        # Create wrapper, passing teardown_list so wrapper can register tasks
        self._current_wrapper = TaskWrapper(
            node=node,
            executor=self._executor,
            tasks_dict=self._task_control.tasks,
            teardown_list=self._teardown_list,
        )

        return self._current_wrapper

    def _check_node_status(self, node):
        """Determine if task should run, is up-to-date, etc."""
        if node.run_status is not None:
            return  # Already determined

        task = node.task
        task.overwrite_verbosity(self._stream)

        # Check ignored
        if node.ignored_deps or self._dep_manager.status_is_ignore(task):
            node.run_status = 'ignore'
            return

        # Check bad deps
        if node.bad_deps:
            node.run_status = 'failure'
            return

        # Check up-to-date
        status, error = self._executor.get_task_status(task, self._task_control.tasks)
        if error:
            node.run_status = 'error'
            return

        node.run_status = status

        # Load cached values if up-to-date
        if node.run_status == 'up-to-date':
            task.values = self._dep_manager.get_values(task.name)

    def add_task(self, task):
        """Add a task dynamically and inject it for execution.

        The task will be registered in the task control and scheduled
        for execution in the current iteration.

        @param task: Task instance or dict with task definition
        @return: The added Task instance
        @raise TypeError: If task is not a Task or dict
        @raise InvalidTask: If task name already exists or has invalid deps
        """
        # Convert dict to Task if needed
        if isinstance(task, dict):
            task = dict_to_task(task)
        elif not isinstance(task, Task):
            raise TypeError(f"Expected Task or dict, got {type(task)}")

        # Add to task control (validates deps and registers task)
        self._task_control.add_task(task)

        # Inject into dispatcher to be yielded
        self._dispatcher.inject_task(task.name)

        return task

    def add_tasks(self, tasks):
        """Add multiple tasks dynamically.

        @param tasks: List of Task instances or dicts
        @return: List of added Task instances
        """
        return [self.add_task(t) for t in tasks]

    def finish(self):
        """Finalize: run teardowns and close DB.

        Call this when done iterating, or use DoitEngine context manager.
        """
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self._finished = True

        # Run teardowns in reverse order
        for task in reversed(self._teardown_list):
            task.execute_teardown(self._stream)

        # Close dependency manager
        self._dep_manager.close()


def create_task_iterator(tasks, dep_manager=None, selected=None,
                         always_execute=False, verbosity=0):
    """Create a TaskIterator for programmatic task execution.

    Args:
        tasks: List of Task objects or task dicts (with 'name', 'actions', etc.)
        dep_manager: State storage backend. Can be:
            - None: Use default file-based database (.doit.db)
            - ProcessingStateStore instance: InMemoryStateStore() for no persistence
            - Dependency instance: For custom checker configuration
        selected: List of task names to run (None = all)
        always_execute: Force execution even if up-to-date
        verbosity: Output verbosity (0, 1, or 2)

    Returns:
        TaskIterator instance

    Example:
        tasks = [
            {'name': 'build', 'actions': ['make']},
            {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
        ]

        # File-based persistence (default)
        iterator = create_task_iterator(tasks)
        for task in iterator:
            print(f"Task: {task.name}, should_run: {task.should_run}")
            if task.should_run:
                result = task.execute_and_submit()
        iterator.finish()

        # In-memory execution
        from doit.dependency import InMemoryStateStore
        iterator = create_task_iterator(tasks, dep_manager=InMemoryStateStore())
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

    # Create dependency manager if not provided
    if dep_manager is None:
        dep_manager = Dependency(DbmDB, '.doit.db')
    elif isinstance(dep_manager, ProcessingStateStore):
        # Allow passing a backend directly (convenience)
        dep_manager = Dependency(dep_manager)
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
        tasks = [
            {'name': 'build', 'actions': ['make']},
            {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
        ]

        with DoitEngine(tasks) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

    Example (explicit finish):
        engine = DoitEngine(tasks, dep_manager=dep_manager)
        try:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
        finally:
            engine.finish()

    For in-memory execution (no persistence):
        from doit.dependency import InMemoryStateStore
        engine = DoitEngine(tasks, dep_manager=InMemoryStateStore())
    """

    def __init__(self, tasks, dep_manager=None, selected=None,
                 always_execute=False, verbosity=0):
        """Initialize DoitEngine and create the task iterator.

        @param tasks: List of Task objects or task dicts
        @param dep_manager: State storage backend. Can be:
            - None: Use default file-based database (.doit.db)
            - ProcessingStateStore instance: InMemoryStateStore() for no persistence
            - Dependency instance: For custom checker configuration
        @param selected: List of task names to run (None = all)
        @param always_execute: Force execution even if up-to-date
        @param verbosity: Output verbosity (0, 1, or 2)
        """
        self._iterator = create_task_iterator(
            tasks,
            dep_manager=dep_manager,
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
        """Add a new task dynamically. Delegates to TaskIterator."""
        return self._iterator.add_task(task)

    def add_tasks(self, tasks):
        """Add multiple tasks. Delegates to TaskIterator."""
        return self._iterator.add_tasks(tasks)

    @property
    def tasks(self):
        """Access all tasks dict. Delegates to TaskIterator."""
        return self._iterator.tasks

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False  # Don't suppress exceptions


# Re-export commonly used items
__all__ = [
    'TaskIterator',
    'create_task_iterator',
    'DoitEngine',
    'TaskWrapper',
    'TaskStatus',
]
