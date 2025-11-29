"""Type-safe registry wrappers for task control.

These classes wrap the plain dicts used in TaskControl and TaskDispatcher,
providing a clearer API and enabling future enhancements like validation.
"""

from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..task import Task


class TaskRegistry:
    """Type-safe mapping of task names to Task objects.

    Wraps the tasks dict in TaskControl, providing a cleaner interface
    and enabling iteration, membership testing, and safe lookups.
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        """Add a task to the registry."""
        self._tasks[task.name] = task

    def get(self, name: str) -> Optional[Task]:
        """Get a task by name, or None if not found."""
        return self._tasks.get(name)

    def __getitem__(self, name: str) -> Task:
        """Get a task by name, raising KeyError if not found."""
        return self._tasks[name]

    def __contains__(self, name: str) -> bool:
        """Check if a task name exists in the registry."""
        return name in self._tasks

    def __iter__(self) -> Iterator[str]:
        """Iterate over task names."""
        return iter(self._tasks)

    def __len__(self) -> int:
        """Return the number of tasks."""
        return len(self._tasks)

    def values(self) -> Iterator[Task]:
        """Iterate over Task objects."""
        return iter(self._tasks.values())

    def items(self) -> Iterator[tuple[str, Task]]:
        """Iterate over (name, task) pairs."""
        return iter(self._tasks.items())


class TargetRegistry:
    """Maps target file paths to task names.

    Used to resolve file dependencies into task dependencies
    when a task's file_dep matches another task's target.
    """

    def __init__(self):
        self._targets: dict[str, str] = {}

    def register(self, target_path: str, task_name: str) -> None:
        """Register a target file as produced by a task."""
        self._targets[target_path] = task_name

    def get_task_for_target(self, target_path: str) -> Optional[str]:
        """Get the task name that produces a target, or None."""
        return self._targets.get(target_path)

    def __contains__(self, target_path: str) -> bool:
        """Check if a target path is registered."""
        return target_path in self._targets

    def __getitem__(self, target_path: str) -> str:
        """Get task name for target, raising KeyError if not found."""
        return self._targets[target_path]


class ExecNodeRegistry:
    """Manages ExecNode instances by task name.

    Each task being processed gets an ExecNode to track its execution state.
    This registry ensures we create nodes lazily and reuse them.
    """

    def __init__(self, tasks: TaskRegistry):
        self._nodes: dict[str, Any] = {}  # ExecNode values
        self._tasks = tasks

    def get(self, task_name: str) -> Optional[Any]:
        """Get an existing node, or None if not created yet."""
        return self._nodes.get(task_name)

    def get_or_create(self, task_name: str, parent: Optional[Any]) -> Any:
        """Get existing node or create a new one.

        @param task_name: Name of the task
        @param parent: Parent node (for ancestor tracking)
        @return: The ExecNode for this task
        """
        # Import here to avoid circular dependency
        from ._control import ExecNode

        node = self._nodes.get(task_name)
        if node is None:
            task = self._tasks[task_name]
            node = ExecNode(task, parent)
            self._nodes[task_name] = node
        return node

    def __contains__(self, task_name: str) -> bool:
        """Check if a node exists for this task."""
        return task_name in self._nodes

    def __getitem__(self, task_name: str) -> Any:
        """Get node by task name, raising KeyError if not found."""
        return self._nodes[task_name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over task names with nodes."""
        return iter(self._nodes)

    def values(self) -> Iterator[Any]:
        """Iterate over ExecNode objects."""
        return iter(self._nodes.values())
