"""Callback protocols for task execution lifecycle.

This module provides the ExecutionCallbacks protocol that allows external
code to receive notifications during task execution. This is used by Runner
to integrate reporter callbacks, while keeping TaskIterator focused on
iteration logic.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ExecutionCallbacks(Protocol):
    """Protocol for task execution lifecycle callbacks.

    Implementations receive notifications at key points during task execution.
    All methods are optional - the NullCallbacks class provides no-op defaults.
    """

    def on_status_check(self, task) -> None:
        """Called when checking task status (before determining if it should run)."""
        ...

    def on_skip_uptodate(self, task) -> None:
        """Called when task is skipped because it's up-to-date."""
        ...

    def on_skip_ignored(self, task) -> None:
        """Called when task is skipped because it's ignored."""
        ...

    def on_execute(self, task) -> None:
        """Called immediately before task execution."""
        ...

    def on_success(self, task) -> None:
        """Called after successful task execution and result submission."""
        ...

    def on_failure(self, task, error) -> None:
        """Called after failed task execution.

        @param task: The task that failed
        @param error: BaseFail instance describing the failure
        """
        ...

    def on_teardown(self, task) -> None:
        """Called before running task teardown."""
        ...


class NullCallbacks:
    """Default no-op implementation of ExecutionCallbacks.

    All methods do nothing, making callbacks optional for callers
    that don't need lifecycle notifications.
    """

    def on_status_check(self, task) -> None:
        pass

    def on_skip_uptodate(self, task) -> None:
        pass

    def on_skip_ignored(self, task) -> None:
        pass

    def on_execute(self, task) -> None:
        pass

    def on_success(self, task) -> None:
        pass

    def on_failure(self, task, error) -> None:
        pass

    def on_teardown(self, task) -> None:
        pass


# Singleton instance for default use
_null_callbacks = NullCallbacks()


def get_null_callbacks():
    """Return the singleton NullCallbacks instance."""
    return _null_callbacks
