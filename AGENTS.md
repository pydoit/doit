# Doit Codebase Guide

## Package Structure

```
doit/
├── __init__.py          # Public API exports
├── api.py               # Programmatic execution API (run, run_tasks)
├── doit_cmd.py          # CLI entry point (DoitMain)
├── task.py              # Task class and task definition
├── action.py            # Action classes (CmdAction, PythonAction)
├── loader.py            # Task loading from dodo.py files
├── cmdparse.py          # Command-line argument parsing
├── dependency.py        # Dependency tracking and state storage
├── reporter.py          # Output reporters (console, json, etc.)
├── exceptions.py        # Exception classes
├── globals.py           # Global state (Globals singleton)
├── tools.py             # Helper utilities for task authors
├── plugin.py            # Plugin system
├── version.py           # Version string
│
├── cmd/                 # CLI commands
│   ├── base.py          # Command base classes, loaders
│   ├── run.py           # `doit run` - execute tasks
│   ├── list.py          # `doit list` - list tasks
│   ├── info.py          # `doit info` - task metadata
│   ├── clean.py         # `doit clean` - remove targets
│   ├── forget.py        # `doit forget` - clear task state
│   ├── ignore.py        # `doit ignore` - skip tasks
│   ├── strace.py        # `doit strace` - find deps via strace
│   ├── dumpdb.py        # `doit dumpdb` - dump state db
│   ├── resetdep.py      # `doit reset-dep` - reset deps
│   ├── completion.py    # Shell completion scripts
│   └── help.py          # Help command
│
├── control/             # Task graph and execution control
│   ├── _control.py      # TaskControl, TaskDispatcher, ExecNode
│   └── types.py         # TaskRunStatus enum
│
├── runner/              # Task execution
│   ├── __init__.py      # Runner, MThreadRunner
│   ├── types.py         # ResultCode enum
│   └── executor.py      # TaskExecutor (single task execution)
│
├── engine/              # Programmatic execution engine
│   ├── __init__.py      # DoitEngine main class
│   ├── engine.py        # Engine implementation
│   ├── iterator.py      # TaskIterator for manual control
│   ├── wrapper.py       # TaskWrapper for task execution
│   ├── status.py        # TaskStatus constants
│   └── callbacks.py     # Execution callbacks interface
│
└── state/               # (Reserved for future state components)
```

## Core Concepts

### Task Flow
1. **Loading**: `loader.py` reads `dodo.py`, finds `task_*` functions
2. **Control**: `control/` builds dependency graph, determines execution order
3. **Running**: `runner/` executes tasks, reports results
4. **State**: `dependency.py` tracks file checksums, task completion

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `Task` | `task.py` | Represents a single task with actions, deps, targets |
| `TaskControl` | `control/_control.py` | Manages task graph and dependencies |
| `TaskDispatcher` | `control/_control.py` | Yields tasks in execution order |
| `Runner` | `runner/__init__.py` | Orchestrates task execution with reporting |
| `Dependency` | `dependency.py` | Facade for state storage and up-to-date checking |
| `DoitMain` | `doit_cmd.py` | CLI application entry point |
| `DoitEngine` | `engine/engine.py` | Programmatic execution without CLI |

### Execution Modes

**CLI Mode** (`doit run`):
```
DoitMain → Command.execute() → Runner → TaskDispatcher → Task.execute()
```

**Programmatic Mode** (`DoitEngine`):
```
DoitEngine.run() → Runner (same as CLI)
DoitEngine.tasks() → TaskIterator → TaskWrapper.execute()
```

## State Storage

`dependency.py` handles persistence with pluggable backends:
- `DbmDB` - Default DBM-based storage
- `JsonDB` - JSON file storage
- `SqliteDB` - SQLite database
- `InMemoryStateStore` - In-memory (no persistence)

Key storage prefixes (see `StorageKey` class):
- `_values_:` - Task output values
- `result:` - Task result hash
- `checker:` - File checker class name
- `deps:` - List of file dependencies
- `ignore:` - Task ignore flag

## Enums and Constants

| Enum | Location | Values |
|------|----------|--------|
| `TaskRunStatus` | `control/types.py` | PENDING, RUN, UPTODATE, IGNORE, ERROR, FAILURE, SUCCESSFUL |
| `ResultCode` | `runner/types.py` | SUCCESS (0), FAILURE (1), ERROR (2) |
| `TaskStatus` | `engine/status.py` | PENDING, READY, RUNNING, SUCCESS, FAILURE, SKIPPED_*, ERROR |
| `DependencyReason` | `dependency.py` | Reasons for task not being up-to-date |

## Tests

Tests mirror the source structure in `tests/`:
- `test_task.py` - Task class tests
- `test_dependency.py` - State storage tests
- `test_control.py` - Task graph tests
- `test_runner.py` - Execution tests
- `test_cmd_*.py` - Command tests
- `test_programmatic.py` - DoitEngine tests

Run tests: `python -m pytest`

## Extension Points

- **Custom commands**: Subclass `cmd.base.Command` or `cmd.base.DoitCmdBase`
- **Task loaders**: Subclass `cmd.base.TaskLoader2`
- **Reporters**: Implement reporter interface in `reporter.py`
- **File checkers**: Subclass `FileChangedChecker` in `dependency.py`
- **Uptodate callables**: Subclass `UptodateCalculator` in `dependency.py`

## Documentation Structure

Documentation is in `doc/` using Sphinx:

```
doc/
├── contents.rst          # Master TOC
├── install.rst           # Installation instructions
├── usecases.rst          # Use case examples
├── tutorial-1.rst        # Getting started tutorial
├── tasks.rst             # Task concepts and terminology
├── task-creation.rst     # How to create tasks
├── task-args.rst         # Task arguments and parameters
├── dependencies.rst      # Dependency tracking (file deps, task deps)
├── uptodate.rst          # Up-to-date checking
├── globals.rst           # Global state utilities
├── tools.rst             # Helper tools for task authors
├── cmd-run.rst           # `doit run` command reference
├── cmd-other.rst         # Other CLI commands reference
├── configuration.rst     # Configuration options (doit.cfg, pyproject.toml)
├── extending.rst         # Extending doit (commands, reporters, loaders)
├── programmatic.rst      # Programmatic API (DoitEngine, TaskIterator)
├── faq.rst               # Frequently asked questions
├── related.rst           # Related tools and projects
├── support.rst           # Getting help
├── stories.rst           # Success stories
├── samples/              # 64 example dodo.py files
│   ├── hello.py          # Simple hello world
│   ├── subtasks.py       # Subtask generation
│   ├── getargs.py        # Value passing between tasks
│   └── ...               # Many more examples
└── tutorial/             # Tutorial files
```

### Key Documentation Files

| File | Content |
|------|---------|
| `programmatic.rst` | DoitEngine API, TaskWrapper, callbacks, concurrent execution |
| `tasks.rst` | Task attributes (actions, deps, targets, uptodate) |
| `dependencies.rst` | File deps, task deps, calculated deps, getargs |
| `extending.rst` | Custom commands, reporters, loaders, plugins |
| `configuration.rst` | doit.cfg format, pyproject.toml integration |

### Examples

- `doc/samples/` - 64 example dodo.py files demonstrating features
- `examples/programmatic_demo/` - Programmatic API demo scripts
- `doc/tutorial/` - Step-by-step tutorial files

### Documentation Tests

Tests validate documentation examples work correctly:
- `tests/test_doc_examples.py` - Programmatic API examples
- `tests/test_doc_samples.py` - All 64 doc/samples files
