================
Developer's docs
================

This document presents a general overview of how `doit` works. If you just want to use `doit`, you better take a look at the tutorial_. 


Package modules
---------------     

- __init__.py: (empty) make a package
- `dependency.py <api/doit.dependency-module.html>`_: Manage (save/check) task dependency-on-files data.
- `loader.py <api/doit.loader-module.html>`_: Loads a python module and extracts its task generator functions.
- `logger.py <api/doit.logger-module.html>`_: Logger with channel support.
- `main.py <api/doit.main-module.html>`_: `doit` command line program.
- `runner.py <api/doit.runner-module.html>`_: Task runner.
- `task.py <api/doit.task-module.html>`_: Task classes.
- `util.py <api/doit.util-module.html>`_: Utility methods.


Execution flow
--------------

`doit` is invoked using the script ``bin/doit``. It uses optparse_ to parse the command line arguments and create a Main_ instance. And then calls ``Main.process``.

Main_ is responsible for controlling the whole execution. It has 6 stages:

#. load dodo(configuration) file with "task generators"
#. get tasks from task generators
#. set task's task-dependencies
#. filter selected tasks
#. add selected tasks to runner
#. execute tasks 


Load "task generators"
^^^^^^^^^^^^^^^^^^^^^^

Tasks are defined on the configuration file (from now on called "dodo" file). The dodo file is a plain python module. 

The Loader_ will first import the dodo file. Than it introspects the module collecting all functions named with a starting ``task_``. These functions are "task generators", they are not tasks on its own but they build tasks. 

The task generators are ordered by the line where they were defined. By default tasks are executed in this order.



Get tasks from task generators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
Generators return python dictionaries to represent tasks. The task name is given by function name of the task generator less the initial string ``task_``. For example the task name for "task_doXYZ" would be "doXYZ".

There is only one required field: 'action'. This field describes the action executed by the task. It can optionally define 'dependencies' and 'targets'. See reference_ for a complete list of accepted fields. 

As a convenience to users if the task only defines an ``action`` they don't need to return it in a dictionary. 

There are two kinds of tasks generators. Task generators that define a single a task, or define multiple subtasks. To define multiple subtasks instead of returning a single dictionary it must return a generator using `python-generator <http://docs.python.org/tut/node11.html#SECTION00111000000000000000000>`_

Subtasks must include the field ``name`` on its dictionary representation. A subtask name will be formed as "<task_name>:<subTask_name>".



Set task's task-dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Collect all task-dependencies for every task. task-dependencies can come from 3 sources.

#. A task generator that return maultiple subtasks creates a dumb task with no action that depends on all subtasks.

#. A task-dependency explicit defined in the 'dependecies' as ":<dependends-on-task_name>".

#. A file-dependency where the file is also a target from another task. If task-B dependends on file-TA and file-TA is a target of task-A, task-B depends on task-A. Or task-A is a task-dependency of task-B.


Filter selected tasks
^^^^^^^^^^^^^^^^^^^^^

From the command line the user can choose which tasks to execute (by default all tasks are executed). see reference_ for all command line option parameters. In this case the tasks are executed in the order they were list in the command line (not in the order they were defined).


Just go over all the defined tasks and select the ones present in the list filter. If no list filter is defined all tasks are selected.


Add selected tasks to runner
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The selected tasks are added to the _Runner in the order they will be executed. If task has any task-dependency they are added before the task being processed. Tasks are never added twice. Task can not have cyclic dependency, it is detected and an error is reported.


Execute tasks
^^^^^^^^^^^^^

At this point the _Runner has a list of all tasks that will be executed and its file-dependencies and targets.

The runner executes only tasks that are not up-to-date. A dbm_ (simple "database
" interface) is used to keep information on tasks and their file-dependencies. Each entry is: key=>  taskId + dependency (abs file path), value=>  signature(md5) the dependency content.


Targets are treated as file-dependencies. The only difference is that if a dependency file is not on the file system an error is raised. While targets are not required to exist on the file system before the task is executed.

The following rules apply to dependencies (targets also):

- if a task does not define any file-dependency or True (run-once) it is always executed.
- if none of the file-dependencies is not modified (changed its signature) the task action is not executed
- if the task is completed successfully all dependency records are updated.

In case any task fails the whole execution is aborted. 

And, that's it :)

---------------------

You can find more details on how each module work in the `API docs <api/index.html>`_.


.. _tutorial: tutorial.html
.. _reference: reference.html

.. _optparse: http://docs.python.org/lib/module-optparse.html
.. _dbm: http://docs.python.org/lib/module-anydbm.html

.. _Main: api/doit.main.Main-class.html
.. _Loader: api/doit.loader.Loader-class.html
.. _Runner: api/doit.runner.Runner-class.html

