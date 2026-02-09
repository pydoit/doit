**Define tasks in Python. Run only what changed.**

*doit* is a task management & automation tool like ``make``, but in pure Python.
It tracks file dependencies, caches results, and skips tasks that are already
up-to-date. No DSL, no YAML - just Python functions.


Quick Example
=============

Create a ``dodo.py``:

.. code:: python

  def task_hello():
      """create a greeting file"""
      return {
          'actions': ['echo "Hello from doit" > hello.txt'],
          'targets': ['hello.txt'],
          'clean': True,
      }

  def task_shout():
      """convert greeting to uppercase"""
      return {
          'actions': ['tr a-z A-Z < hello.txt > shout.txt'],
          'file_dep': ['hello.txt'],
          'targets': ['shout.txt'],
          'clean': True,
      }

Run it:

.. code:: console

  $ pip install doit
  $ doit
  .  hello
  .  shout
  $ doit            # nothing to do - already up-to-date
  -- hello
  -- shout


Key Features
============

- **Incremental builds** - tracks file dependencies and targets,
  re-runs only what changed
- **DAG execution** - tasks run in correct dependency order
- **Python-native** - tasks are plain Python dicts and functions,
  use any library
- **Parallel execution** - run independent tasks concurrently
  (multiprocessing or threading)
- **Subtask generation** - ``yield`` multiple tasks from a single function
- **Computed dependencies** - ``calc_dep`` for dynamic dependency graphs
- **Plugin architecture** - extensible commands, reporters, backends,
  and task loaders


Project Details
===============

 - Website & docs - `https://pydoit.org <https://pydoit.org>`_
 - Project management on github - `https://github.com/pydoit/doit <https://github.com/pydoit/doit>`_
 - Discussion group - `https://groups.google.com/forum/#!forum/python-doit <https://groups.google.com/forum/#!forum/python-doit>`_
 - X/twitter - `https://x.com/pydoit <https://x.com/pydoit>`_

license
=======

The MIT License
Copyright (c) 2008-2026 Eduardo Naufel Schettino
