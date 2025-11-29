"""Task selection and filtering logic.

Handles selection of tasks by name, pattern, target, or regex.
Extracted from TaskControl to isolate the task selection concerns.
"""

from __future__ import annotations
import fnmatch
import re
from typing import TYPE_CHECKING, Sequence

from ..exceptions import InvalidCommand
from ..task import Task

if TYPE_CHECKING:
    from collections import OrderedDict


class RegexGroup:
    """Helper to track delayed-tasks matched by regex target.

    When a target specified on command line matches a task's target_regex,
    this tracks which delayed-tasks could potentially produce that target.
    """

    def __init__(self, target: str, tasks: set[str]):
        self.target = target  # target name specified in command line
        self.tasks = tasks  # set of delayed-task names (strings)
        self.found = False  # whether the target was already found


class TaskSelector:
    """Selects tasks based on command-line arguments.

    Handles several selection mechanisms:
    - Direct task name
    - Wildcard patterns (e.g., 'test:*')
    - Target file paths
    - Delayed task subtasks
    - Regex target matching
    """

    def __init__(
        self,
        tasks: OrderedDict[str, Task],
        targets: dict[str, str],
        auto_delayed_regex: bool = False,
    ):
        """
        @param tasks: task name -> Task mapping
        @param targets: target file -> task name mapping
        @param auto_delayed_regex: if True, treat all delayed tasks as regex-capable
        """
        self._tasks = tasks
        self._targets = targets
        self._auto_delayed_regex = auto_delayed_regex

    def select(self, task_selection: Sequence[str]) -> list[str]:
        """Select tasks from command-line arguments.

        @param task_selection: list of task names/params/targets from command line
        @return: list of task names to execute
        @raise InvalidCommand: if a specified task/target is not found
        """
        selected = []
        filter_list = self._process_filter(task_selection)

        for filter_ in filter_list:
            task_name = self._resolve_filter(filter_)
            if task_name:
                selected.append(task_name)
                continue

            selected.extend(self._resolve_delayed(filter_))

        return selected

    def get_wild_tasks(self, pattern: str, task_order: list[str]) -> list[str]:
        """Get list of tasks matching a wildcard pattern.

        @param pattern: glob-style pattern (e.g., 'test:*')
        @param task_order: task names in definition order
        @return: list of matching task names
        """
        return [name for name in task_order if fnmatch.fnmatch(name, pattern)]

    def _process_filter(self, task_selection: Sequence[str]) -> list[str]:
        """Process command-line task options.

        Format: [task_name [-task_opt [opt_value]] ...] ...

        @param task_selection: list of strings with task names/params or target
        @return: list of task names with glob expanded and params consumed
        """
        filter_list = []
        seq = list(task_selection)

        while seq:
            f_name = seq.pop(0)

            # Wildcard pattern expands to multiple tasks
            if '*' in f_name:
                for task_name in self._tasks:
                    if fnmatch.fnmatch(task_name, f_name):
                        filter_list.append(task_name)
            else:
                filter_list.append(f_name)
                # Parse task options if this is a known task
                if f_name in self._tasks:
                    seq = self._consume_task_options(f_name, seq)

        return filter_list

    def _consume_task_options(self, task_name: str, remaining: list[str]) -> list[str]:
        """Consume task options and positional args from remaining args.

        @param task_name: name of the task to configure
        @param remaining: remaining command-line arguments
        @return: unconsumed arguments
        """
        task = self._tasks[task_name]
        remaining = task.init_options(remaining)

        if task.pos_arg is not None and task.pos_arg_val is None:
            task.pos_arg_val = remaining
            remaining = []

        return remaining

    def _resolve_filter(self, filter_: str) -> str | None:
        """Try to resolve filter as task name or target.

        @return: task name or None if not found
        """
        # Direct task name
        if filter_ in self._tasks:
            return filter_

        # Target file -> task name
        if filter_ in self._targets:
            return self._targets[filter_]

        return None

    def _resolve_delayed(self, filter_: str) -> list[str]:
        """Resolve filter as delayed task subtask or regex target.

        @param filter_: filter string that wasn't a direct task/target
        @return: list of task names (may be empty)
        @raise InvalidCommand: if filter can't be resolved
        """
        # Check if it's a subtask of a delayed task
        basename = filter_.split(':', 1)[0]
        if basename in self._tasks:
            task = self._tasks[basename]
            if task.loader:
                task.loader.basename = basename
                self._tasks[filter_] = Task(filter_, None, loader=task.loader)
                return [filter_]
            raise InvalidCommand(not_found=filter_)

        # Check regex target matching
        return self._resolve_regex_target(filter_)

    def _resolve_regex_target(self, filter_: str) -> list[str]:
        """Create tasks to load delayed tasks that might produce target.

        @param filter_: target path that might match a task's target_regex
        @return: list of regex-target task names
        @raise InvalidCommand: if no delayed tasks match
        """
        delayed_matched = []
        for task in list(self._tasks.values()):
            if not task.loader:
                continue
            if task.name.startswith('_regex_target'):
                continue
            if task.loader.target_regex:
                if re.match(task.loader.target_regex, filter_):
                    delayed_matched.append(task)
            elif self._auto_delayed_regex:
                delayed_matched.append(task)

        if not delayed_matched:
            raise InvalidCommand(not_found=filter_)

        delayed_names = {t.name for t in delayed_matched}
        regex_group = RegexGroup(filter_, delayed_names)
        selected = []

        for task in delayed_matched:
            loader = task.loader
            loader.basename = task.name
            name = f'_regex_target_{filter_}:{task.name}'
            loader.regex_groups[name] = regex_group
            self._tasks[name] = Task(name, None, loader=loader, file_dep=[filter_])
            selected.append(name)

        return selected
