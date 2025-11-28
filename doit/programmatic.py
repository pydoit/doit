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
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

In-memory execution (no database persistence):

    with DoitEngine(tasks, db_file=':memory:') as engine:
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

Dynamic task injection:

    with DoitEngine(initial_tasks, db_file=':memory:') as engine:
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

            # Add new tasks based on results
            if wrapper.name == 'discover':
                for item in wrapper.values.get('discovered', []):
                    engine.add_task({
                        'name': f'process_{item}',
                        'actions': [process_fn],
                    })

Manual iteration (without context manager):

    iterator = create_task_iterator(tasks)
    try:
        for wrapper in iterator:
            if wrapper.should_run:
                wrapper.execute_and_submit()
    finally:
        iterator.finish()  # Run teardowns and close DB
"""

from .control import TaskControl
from .dependency import Dependency, DbmDB, MD5Checker, TimestampChecker
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


def create_task_iterator(tasks, db_file='.doit.db', selected=None,
                         always_execute=False, verbosity=0,
                         db_backend=DbmDB, checker_cls=None):
    """Create a TaskIterator for programmatic task execution.

    Args:
        tasks: List of Task objects or task dicts (with 'name', 'actions', etc.)
        db_file: Path to dependency database, or ':memory:' for in-memory
        selected: List of task names to run (None = all)
        always_execute: Force execution even if up-to-date
        verbosity: Output verbosity (0, 1, or 2)
        db_backend: Database backend class (ignored if db_file is ':memory:')
        checker_cls: File change checker class (defaults based on db_file)

    Returns:
        TaskIterator instance

    Example:
        tasks = [
            {'name': 'build', 'actions': ['make']},
            {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
        ]

        iterator = create_task_iterator(tasks)
        for wrapper in iterator:
            print(f"Task: {wrapper.name}, should_run: {wrapper.should_run}")
            if wrapper.should_run:
                result = wrapper.execute_and_submit()
        iterator.finish()
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
    dep_manager = Dependency(db_backend, db_file, checker_cls=checker_cls)
    stream = Stream(verbosity)

    return TaskIterator(
        task_control=task_control,
        dep_manager=dep_manager,
        stream=stream,
        always_execute=always_execute,
    )


class DoitEngine:
    """Context manager for programmatic doit execution.

    Automatically handles cleanup (teardowns and DB close) when exiting
    the context.

    Example:
        tasks = [
            {'name': 'build', 'actions': ['make']},
            {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
        ]

        with DoitEngine(tasks) as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

    For in-memory execution (no persistence):
        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()
    """

    def __init__(self, tasks, **kwargs):
        """Initialize DoitEngine.

        @param tasks: List of Task objects or task dicts
        @param **kwargs: Arguments passed to create_task_iterator
            - db_file: Path to dependency database (default: '.doit.db')
            - selected: List of task names to run (None = all)
            - always_execute: Force execution even if up-to-date
            - verbosity: Output verbosity (0, 1, or 2)
            - db_backend: Database backend class
            - checker_cls: File change checker class
        """
        self._tasks = tasks
        self._kwargs = kwargs
        self._iterator = None

    def __enter__(self):
        self._iterator = create_task_iterator(self._tasks, **self._kwargs)
        return self._iterator

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._iterator:
            self._iterator.finish()
        return False  # Don't suppress exceptions


# Re-export commonly used items
__all__ = [
    'TaskIterator',
    'create_task_iterator',
    'DoitEngine',
    'TaskWrapper',
    'TaskStatus',
]
