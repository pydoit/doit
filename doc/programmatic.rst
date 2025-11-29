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
- ``store`` - StateStore instance for custom storage (e.g., ``MemoryStore()``).
  If None, uses file-based storage at ``db_path``.
- ``db_path`` - path to database file (default: ``.doit.db``).
  Ignored if ``store`` is provided.
- ``selected`` - list of task names to run (default: all tasks)
- ``always_execute`` - force execution even if up-to-date (default: False)
- ``verbosity`` - output verbosity 0, 1, or 2 (default: 0)

**Methods:**

- ``finish()`` - run teardowns and close database (called automatically by context manager)
- ``add_task(task)`` - add a single task dynamically
- ``add_tasks(task_list)`` - add multiple tasks

**Concurrent execution methods** (see :ref:`concurrent-execution`):

- ``has_pending_tasks`` - property, True if more tasks to process
- ``get_ready_tasks()`` - get all tasks ready for parallel execution
- ``notify_completed(wrapper)`` - notify that a task completed


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

For testing or one-off execution without persistence, use ``MemoryStore``:

.. code-block:: python

    from doit import DoitEngine
    from doit.state import MemoryStore

    with DoitEngine(tasks, store=MemoryStore()) as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()

This uses timestamp-based dependency checking (like Make) instead of
checksums, which is faster and doesn't require previous state.

For file-based persistence with a custom path:

.. code-block:: python

    with DoitEngine(tasks, db_path='/path/to/custom.db') as engine:
        for task in engine:
            if task.should_run:
                task.execute_and_submit()


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


.. _concurrent-execution:

Concurrent Execution
====================

For parallel task execution, use the concurrent execution API with
``ThreadPoolExecutor`` or similar:

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    from doit import DoitEngine
    from doit.state import MemoryStore

    with DoitEngine(tasks, store=MemoryStore()) as engine:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            while engine.has_pending_tasks:
                # Get all tasks that are ready to run
                for task in engine.get_ready_tasks():
                    if task.should_run:
                        future = executor.submit(task.execute)
                        futures[future] = task
                    else:
                        task.submit(None)
                        engine.notify_completed(task)

                # Wait for at least one task to complete
                if futures:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        task = futures.pop(future)
                        task.submit(future.result())
                        engine.notify_completed(task)

**Key methods:**

- ``has_pending_tasks`` - Returns True if there are more tasks to process
- ``get_ready_tasks()`` - Returns list of TaskWrappers for all tasks currently
  ready to execute (no pending dependencies)
- ``notify_completed(wrapper)`` - Call after a task is executed and submitted.
  This updates the dependency graph and may make new tasks ready.
  Returns list of newly ready tasks.

**Important:** You must call ``notify_completed()`` after each task completes
to allow dependent tasks to become ready.


Dynamic Task Injection
======================

Add new tasks during iteration based on results:

.. code-block:: python

    from doit import DoitEngine
    from doit.state import MemoryStore

    def discover_files():
        import glob
        return {'files': glob.glob('*.txt')}

    def process_file(filename):
        print(f"Processing {filename}")
        return True

    initial_tasks = [
        {'name': 'discover', 'actions': [discover_files]},
    ]

    with DoitEngine(initial_tasks, store=MemoryStore()) as engine:
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
        db_path='.doit.db',
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
