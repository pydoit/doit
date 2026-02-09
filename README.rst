================
README
================

.. display some badges

.. image:: https://img.shields.io/pypi/v/doit.svg
    :target: https://pypi.python.org/pypi/doit

.. image:: https://github.com/pydoit/doit/actions/workflows/ci.yml/badge.svg?branch=master
    :target: https://github.com/pydoit/doit/actions/workflows/ci.yml?query=branch%3Amaster

.. image:: https://codecov.io/gh/pydoit/doit/branch/master/graph/badge.svg?token=wxKa1h11zn
    :target: https://codecov.io/gh/pydoit/doit

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.4892136.svg
   :target: https://doi.org/10.5281/zenodo.4892136


pydoit - automation tool
=========================

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
  $ doit clean      # remove generated files
  $ doit            # runs again
  .  hello
  .  shout


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


Links
=====

 - Website & docs - https://pydoit.org
 - Project management on github - https://github.com/pydoit/doit
 - Discussion group - https://groups.google.com/forum/#!forum/python-doit
 - X/twitter - https://x.com/pydoit



license
=======

The MIT License
Copyright (c) 2008-2026 Eduardo Naufel Schettino

see LICENSE file


Financial contributions on `Open Collective <https://opencollective.com/doit/tiers>`_

.. image:: https://opencollective.com/doit/tiers/backers.svg?avatarHeight=50
    :target: https://opencollective.com/doit/tiers
