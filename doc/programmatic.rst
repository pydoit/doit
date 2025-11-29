.. meta::
   :description: How to use doit programmatically with full control over task execution
   :keywords: python, doit, programmatic, API, library, embedding, DoitEngine

.. title:: Programmatic Interface - pydoit guide


======================
Programmatic Interface
======================

.. _programmatic:

While `doit` is primarily used as a command-line tool, it also provides
a programmatic interface for running tasks with full control over execution.
This is useful for:

- Embedding doit in larger applications
- Building custom task runners
- Dynamic task graphs that evolve during execution
- Testing and CI/CD integrations
- Interactive applications that need fine-grained control

Quick Start
===========

The simplest way to run tasks programmatically is with ``DoitEngine``:

.. code-block:: python

    from doit import DoitEngine

    tasks = [
        {'name': 'build', 'actions': ['make']},
        {'name': 'test', 'actions': ['pytest'], 'task_dep': ['build']},
    ]

    with DoitEngine(tasks) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

This will:

1. Create tasks from the dict definitions
2. Iterate through tasks in dependency order
3. Execute each task that needs to run
4. Track results for up-to-date checking on future runs


Key Classes
===========

DoitEngine
----------

The main entry point for programmatic execution. Can be used as a context
manager (recommended) or with explicit ``finish()``.

.. code-block:: python

    from doit import DoitEngine

    # As context manager (recommended)
    with DoitEngine(tasks) as engine:
        for task in engine:
            # process each task
            ...

    # Or with explicit finish
    engine = DoitEngine(tasks)
    try:
        for task in engine:
            ...
    finally:
        engine.finish()

**Parameters:**

- ``tasks`` - list of Task objects or task dicts
- ``dep_manager`` - Dependency instance for state persistence.
  If None, creates a default file-based database (``.doit.db``).
  For in-memory execution, pass ``Dependency(InMemoryStateStore())``.
- ``selected`` - list of task names to run (default: all tasks)
- ``always_execute`` - force execution even if up-to-date (default: False)
- ``verbosity`` - output verbosity 0, 1, or 2 (default: 0)

**Methods:**

- ``finish()`` - run teardowns and close database (called automatically by context manager)
- ``add_task(task)`` - add a single task dynamically
- ``add_tasks(task_list)`` - add multiple tasks


TaskWrapper
-----------

Wraps each task, providing control over execution.

**Core properties:**

- ``name`` - task name
- ``task`` - underlying Task object
- ``actions`` - list of task actions

**Task definition properties** (delegated to underlying task):

- ``file_dep`` - file dependencies (set of paths)
- ``task_dep`` - task dependencies (list of task names)
- ``targets`` - target files (list of paths)
- ``uptodate`` - up-to-date conditions (list)
- ``calc_dep`` - calculated dependencies (set of task names)
- ``setup_tasks`` - setup task names (list)
- ``teardown`` - teardown actions (list)
- ``doc`` - task documentation (str or None)
- ``meta`` - user/plugin metadata (dict or None)
- ``getargs`` - values from other tasks (dict)
- ``verbosity`` - task verbosity level (0, 1, 2, or None)
- ``subtask_of`` - parent task name if subtask (or None)
- ``has_subtask`` - True if task has subtasks

**Execution state properties:**

- ``should_run`` - True if task needs execution
- ``skip_reason`` - why task was skipped (``'up-to-date'`` or ``'ignore'``)
- ``status`` - current TaskStatus
- ``values`` - task output values (available after execution)
- ``executed`` - whether execute() has been called
- ``submitted`` - whether submit() has been called

**Methods:**

- ``execute()`` - run the task's actions, returns error or None
- ``submit(result=None)`` - save results to dependency tracking
- ``execute_and_submit()`` - convenience method combining both


TaskStatus
----------

Enum of possible task states:

- ``TaskStatus.PENDING`` - not yet processed
- ``TaskStatus.READY`` - ready to execute
- ``TaskStatus.RUNNING`` - executed but not submitted
- ``TaskStatus.SUCCESS`` - completed successfully
- ``TaskStatus.FAILURE`` - task failed
- ``TaskStatus.SKIPPED_UPTODATE`` - skipped (up-to-date)
- ``TaskStatus.SKIPPED_IGNORED`` - skipped (ignored)
- ``TaskStatus.ERROR`` - error checking dependencies


In-Memory Execution
===================

For testing or one-off execution without persistence, use ``InMemoryStateStore``:

.. code-block:: python

    from doit import DoitEngine
    from doit.dependency import InMemoryStateStore

    with DoitEngine(tasks, dep_manager=InMemoryStateStore()) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

This uses timestamp-based dependency checking (like Make) instead of
checksums, which is faster and doesn't require previous state.

For file-based persistence with a custom path:

.. code-block:: python

    from doit.dependency import Dependency, DbmDB

    dep_manager = Dependency(DbmDB, '/path/to/custom.db')
    engine = DoitEngine(tasks, dep_manager=dep_manager)

The ``dep_manager`` parameter accepts:

- ``None`` (default): Use file-based database (``.doit.db``)
- ``InMemoryStateStore()`` or other ``ProcessingStateStore``: Automatically wrapped in ``Dependency``
- ``Dependency`` instance: For custom checker configuration


Execution Control
=================

You have three levels of control over task execution:

Simple (execute_and_submit)
---------------------------

Run and save results in one call:

.. code-block:: python

    for task in engine:
        if task.should_run:
            result = task.execute_and_submit()
            if result:
                print(f"Task {task.name} failed: {result}")


Separate (execute + submit)
---------------------------

Execute first, inspect results, then submit:

.. code-block:: python

    for task in engine:
        if task.should_run:
            result = task.execute()

            # Inspect before committing
            if result is None:
                print(f"{task.name} succeeded, values: {task.values}")
            else:
                print(f"{task.name} failed: {result}")

            task.submit()


Manual (access actions directly)
--------------------------------

Access raw actions for custom execution:

.. code-block:: python

    for task in engine:
        if task.should_run:
            for action in task.actions:
                # Custom execution logic
                print(f"Would run: {action}")


Custom Skip Logic
-----------------

Skip tasks based on your own criteria:

.. code-block:: python

    skip_tasks = {'slow_test', 'integration_test'}

    for task in engine:
        if task.name in skip_tasks:
            continue  # Skip without executing or submitting

        if task.should_run:
            task.execute_and_submit()


Dynamic Task Injection
======================

Add new tasks during iteration based on results:

.. code-block:: python

    from doit import DoitEngine
    from doit.dependency import Dependency, InMemoryStateStore

    def discover_files():
        import glob
        return {'files': glob.glob('*.txt')}

    def process_file(filename):
        print(f"Processing {filename}")
        return True

    initial_tasks = [
        {'name': 'discover', 'actions': [discover_files]},
    ]

    dep_manager = Dependency(InMemoryStateStore())
    with DoitEngine(initial_tasks, dep_manager=dep_manager) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

            # Add tasks based on discovery results
            if task.name == 'discover':
                for f in task.values.get('files', []):
                    engine.add_task({
                        'name': f'process_{f}',
                        'actions': [(process_file, [f])],
                        'task_dep': ['discover'],
                    })


Working with Values
===================

Tasks can return values that are passed to dependent tasks:

.. code-block:: python

    def producer():
        """Action that returns values."""
        return {'result': 42, 'status': 'ok'}

    def consumer(result):
        """Action that uses values from producer."""
        print(f"Got result: {result}")
        return True

    tasks = [
        {'name': 'produce', 'actions': [producer]},
        {
            'name': 'consume',
            'actions': [(consumer,)],  # Tuple form for kwargs from options
            'getargs': {'result': ('produce', 'result')},
            'task_dep': ['produce'],
        },
    ]

After execution, access values via ``task.values``:

.. code-block:: python

    for task in engine:
        if task.should_run:
            task.execute_and_submit()
            if task.values:
                print(f"{task.name} returned: {task.values}")


Manual Iteration
================

For more control, use ``create_task_iterator`` directly:

.. code-block:: python

    from doit import create_task_iterator

    iterator = create_task_iterator(
        tasks,
        db_file='.doit.db',
        selected=['task1', 'task2'],
        always_execute=False,
        verbosity=1,
    )

    try:
        for task in iterator:
            if task.should_run:
                task.execute_and_submit()
    finally:
        iterator.finish()  # Important: run teardowns and close DB


Complete Example
================

A build system that compiles source files:

.. code-block:: python

    from pathlib import Path
    from doit import DoitEngine

    def compile_file(src, out):
        """Compile a source file."""
        content = Path(src).read_text()
        Path(out).write_text(f"# Compiled\n{content}")
        return True

    def link_files(inputs, output):
        """Link compiled files."""
        combined = "\n".join(Path(f).read_text() for f in inputs)
        Path(output).write_text(combined)
        return True

    # Define tasks
    sources = ['a.py', 'b.py', 'c.py']
    tasks = []

    for src in sources:
        out = f"build/{src}.o"
        tasks.append({
            'name': f'compile_{src}',
            'actions': [(compile_file, [src, out])],
            'file_dep': [src],
            'targets': [out],
        })

    tasks.append({
        'name': 'link',
        'actions': [(link_files,
                     [[f"build/{s}.o" for s in sources], "build/app"])],
        'file_dep': [f"build/{s}.o" for s in sources],
        'targets': ['build/app'],
        'task_dep': [f'compile_{s}' for s in sources],
    })

    # Run the build
    with DoitEngine(tasks) as engine:
        for task in engine:
            if task.should_run:
                print(f"Running: {task.name}")
                task.execute_and_submit()
            else:
                print(f"Up-to-date: {task.name}")


See Also
========

- Demo scripts in ``examples/programmatic_demo/``
- :ref:`extending` for creating custom task loaders
- :ref:`tasks` for task definition details
