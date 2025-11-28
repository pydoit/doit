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
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

This will:

1. Create tasks from the dict definitions
2. Iterate through tasks in dependency order
3. Execute each task that needs to run
4. Track results for up-to-date checking on future runs


Key Classes
===========

DoitEngine
----------

A context manager that sets up and tears down the task execution environment.

.. code-block:: python

    from doit import DoitEngine

    with DoitEngine(tasks, db_file='.doit.db') as engine:
        for wrapper in engine:
            # process each task
            ...

**Parameters:**

- ``tasks`` - list of Task objects or task dicts
- ``db_file`` - path to dependency database (default: ``.doit.db``)
  Use ``:memory:`` for in-memory execution without persistence.
- ``selected`` - list of task names to run (default: all tasks)
- ``always_execute`` - force execution even if up-to-date (default: False)
- ``verbosity`` - output verbosity 0, 1, or 2 (default: 0)


TaskWrapper
-----------

Wraps each task, providing control over execution.

**Properties:**

- ``name`` - task name
- ``task`` - underlying Task object
- ``actions`` - list of task actions
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

For testing or one-off execution without persistence, use ``:memory:``:

.. code-block:: python

    with DoitEngine(tasks, db_file=':memory:') as engine:
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

This uses timestamp-based dependency checking (like Make) instead of
checksums, which is faster and doesn't require previous state.


Execution Control
=================

You have three levels of control over task execution:

Simple (execute_and_submit)
---------------------------

Run and save results in one call:

.. code-block:: python

    for wrapper in engine:
        if wrapper.should_run:
            result = wrapper.execute_and_submit()
            if result:
                print(f"Task {wrapper.name} failed: {result}")


Separate (execute + submit)
---------------------------

Execute first, inspect results, then submit:

.. code-block:: python

    for wrapper in engine:
        if wrapper.should_run:
            result = wrapper.execute()

            # Inspect before committing
            if result is None:
                print(f"{wrapper.name} succeeded, values: {wrapper.values}")
            else:
                print(f"{wrapper.name} failed: {result}")

            wrapper.submit()


Manual (access actions directly)
--------------------------------

Access raw actions for custom execution:

.. code-block:: python

    for wrapper in engine:
        if wrapper.should_run:
            for action in wrapper.actions:
                # Custom execution logic
                print(f"Would run: {action}")


Custom Skip Logic
-----------------

Skip tasks based on your own criteria:

.. code-block:: python

    skip_tasks = {'slow_test', 'integration_test'}

    for wrapper in engine:
        if wrapper.name in skip_tasks:
            continue  # Skip without executing or submitting

        if wrapper.should_run:
            wrapper.execute_and_submit()


Dynamic Task Injection
======================

Add new tasks during iteration based on results:

.. code-block:: python

    def discover_files():
        import glob
        return {'files': glob.glob('*.txt')}

    def process_file(filename):
        print(f"Processing {filename}")
        return True

    initial_tasks = [
        {'name': 'discover', 'actions': [discover_files]},
    ]

    with DoitEngine(initial_tasks, db_file=':memory:') as engine:
        for wrapper in engine:
            if wrapper.should_run:
                wrapper.execute_and_submit()

            # Add tasks based on discovery results
            if wrapper.name == 'discover':
                for f in wrapper.values.get('files', []):
                    engine.add_task({
                        'name': f'process_{f}',
                        'actions': [(process_file, [f])],
                        'task_dep': ['discover'],
                    })

**Methods:**

- ``engine.add_task(task)`` - add a single task (dict or Task object)
- ``engine.add_tasks(task_list)`` - add multiple tasks


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

After execution, access values via ``wrapper.values``:

.. code-block:: python

    for wrapper in engine:
        if wrapper.should_run:
            wrapper.execute_and_submit()
            if wrapper.values:
                print(f"{wrapper.name} returned: {wrapper.values}")


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
        for wrapper in iterator:
            if wrapper.should_run:
                wrapper.execute_and_submit()
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
        for wrapper in engine:
            if wrapper.should_run:
                print(f"Running: {wrapper.name}")
                wrapper.execute_and_submit()
            else:
                print(f"Up-to-date: {wrapper.name}")


See Also
========

- Demo scripts in ``examples/programmatic_demo/``
- :ref:`extending` for creating custom task loaders
- :ref:`tasks` for task definition details
