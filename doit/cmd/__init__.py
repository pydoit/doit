"""Command classes for doit CLI.

This package contains all doit command implementations:
- base: Base classes and utilities for commands (Command, DoitCmdBase, loaders)
- run: Run tasks (the default command)
- list: List available tasks
- info: Show task metadata
- clean: Clean task targets
- forget: Forget task state
- ignore: Ignore tasks on subsequent runs
- strace: Use strace to find file dependencies
- dumpdb: Dump dependency database
- completion: Generate shell completion scripts
- resetdep: Reset task dependencies
- help: Help on commands and tasks

Commands exposed from base module:
- Command: Base class for commands that don't use tasks
- DoitCmdBase: Base class for commands that use tasks
- TaskLoader2: Plugin class for task loading
- DodoTaskLoader: Load tasks from dodo.py
- ModuleTaskLoader: Load tasks from a Python module
- get_loader: Get appropriate task loader
"""

# Base classes and loaders
from .base import (
    Command,
    DoitCmdBase,
    TaskLoader2,
    DodoTaskLoader,
    ModuleTaskLoader,
    get_loader,
    version_tuple,
    check_tasks_exist,
    tasks_and_deps_iter,
    subtasks_iter,
    opt_depfile,
)

# Command classes
from .run import Run
from .list import List
from .info import Info
from .clean import Clean
from .forget import Forget
from .ignore import Ignore
from .strace import Strace
from .dumpdb import DumpDB
from .completion import TabCompletion
from .resetdep import ResetDep
from .help import Help

__all__ = [
    # Base classes
    'Command',
    'DoitCmdBase',
    'TaskLoader2',
    'DodoTaskLoader',
    'ModuleTaskLoader',
    'get_loader',
    'version_tuple',
    'check_tasks_exist',
    'tasks_and_deps_iter',
    'subtasks_iter',
    'opt_depfile',
    # Commands
    'Run',
    'List',
    'Info',
    'Clean',
    'Forget',
    'Ignore',
    'Strace',
    'DumpDB',
    'TabCompletion',
    'ResetDep',
    'Help',
]
