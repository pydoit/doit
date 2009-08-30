================
Developer's docs
================

This document presents a general overview of how `doit` works. If you just want to use `doit`, you better take a look at the tutorial_.


Package modules
---------------

- __init__.py: (empty) make a package
- `dependency.py <api/doit.dependency-module.html>`_: Manage (save/check) task dependency-on-files data.
- `logger.py <api/doit.logger-module.html>`_: Logger with channel support.
- `main.py <api/doit.main-module.html>`_: Loads dodo file (a python module) and `doit` command line programs.
- `runner.py <api/doit.runner-module.html>`_: Tasks runner.
- `task.py <api/doit.task-module.html>`_: Task classes.
- `util.py <api/doit.util-module.html>`_: Utility methods.
- `cmdparse.py <api/doit.cmdparse-module.html>`_: Parse command line options and execute it. Built on top of getopt.


Execution flow - command `run`
------------------------------

`doit` is invoked using the script ``bin/doit``. It uses `cmdparse` to parse the command line arguments.

#. the dodo module is loaded (`get_module <api/doit.main-module.html#get_module>`_)
#. collect all task generator functions. (`load_task_generators <api/doit.main-module.html#load_task_generators>`_)
#. task generator functions are executed and the information of generated tasks are saved
#. the "raw" task information is processed (`TaskSetup <api/doit.main.TaskSetup-class.html>`_). tasks are organized (sorted) in an order to fulfill their dependencies.
#. filter selected tasks
#. run selected tasks `run_tasks <api/doit.runner-module.html#run_tasks>`_


Load "task generators"
^^^^^^^^^^^^^^^^^^^^^^

Tasks are defined on the configuration file (from now on called "dodo" file). The dodo file is a plain python module.

First it imports the dodo file. Than it introspects the module collecting all functions named with a starting ``task_``. These functions are "task generators", they are not tasks on its own but they build tasks.

The task generators are ordered by the line where they were defined. By default tasks are executed in this order.



Get tasks from task generators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generators return python dictionaries to represent tasks. The task name is given by function name of the task generator less the initial string ``task_``. For example the task name for "task_doXYZ" would be "doXYZ".

As a convenience to users if the task only defines an ``action`` they don't need to return it in a dictionary.

There are two kinds of tasks generators. Task generators that define a single a task, or define multiple sub-tasks. To define multiple sub-tasks instead of returning a single dictionary it must return a generator using `python-generator <http://docs.python.org/tut/node11.html#SECTION00111000000000000000000>`_

Sub-tasks must include the field ``name`` on its dictionary representation. A sub-task name will be formed as "<task_name>:<subTask_name>".



Set task's task-dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Collect all task-dependencies for every task. task-dependencies can come from 3 sources.

#. A task generator that return multiple sub-tasks creates a dumb task with no action that depends on all sub-tasks.

#. A task-dependency explicit defined in the 'dependencies' as ":<depends-on-task_name>".

#. A file-dependency where the file is also a target from another task. If task-B depends on file-TA and file-TA is a target of task-A, task-B depends on task-A. Or task-A is a task-dependency of task-B.


Filter selected tasks
^^^^^^^^^^^^^^^^^^^^^

From the command line the user can choose which tasks to execute (by default all tasks are executed). The dodo file can also define a list DEFAULT_TASKS. In this case the tasks are executed in the order they were list in the command line (not in the order they were defined).


Just go over all the defined tasks and select the ones present in the list filter. If no list filter is defined all tasks are selected.


Order tasks
^^^^^^^^^^^

The selected tasks are sorted in the order they will be executed. If task has any task-dependency they are added before the task being processed. Tasks are never added twice. Task can not have cyclic dependency, it is detected and an error is reported.


Execute tasks
^^^^^^^^^^^^^

The runner executes only tasks that are not up-to-date. A db file (using JSON format) is used to keep information on tasks and their file-dependencies. there is a dictionary for every task. each task has a dictionary where key is  dependency (abs file path), and the value is the dependency signature.

The following rules apply to dependencies:

- if a task does not define any file-dependency or True (run-once) it is always executed.
- if none of the file-dependencies is not modified (changed its signature) the task action is not executed
- if the task is completed successfully all dependency records are updated.

If a target does not exist the task is executed.

If a task is a "run-once" (has a dependency True). It will not be executed after the first successful run. As long as its execution is not forced by a target.

In case any task fails the whole execution is aborted.

And, that's it :)

---------------------

You can find details on how each module work in the `API docs <api/index.html>`_.


.. _tutorial: tutorial.html
.. _reference: reference.html
