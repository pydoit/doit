========
Tasks
========

Intro
-------

`doit` is all about automating task dependency management and execution. Tasks can execute external shell commands/scripts or python functions (actually any callable). So a task can be anything you can code :)

Tasks are defined using `python <http://python.org/>`_, in a plain python file with some conventions. A function that starts with the name `task_` defines a *task generator* recognized by `doit`. These functions must return (or yield) dictionaries representing a *task*. A python module/file that defines *tasks* for `doit` is called **dodo** file (that is something like a `Makefile` for `make`).

.. note::

    You should be comfortable with python basics. If you don't know python yet check `Python tutorial <http://docs.python.org/tut/>`_ and `Dive Into Python <http://www.diveintopython.org/>`_.


Take a look at this example (file dodo.py):

.. literalinclude:: tutorial/tutorial_01.py

When `doit` is executed without any parameters it will look for tasks in a file named `dodo.py` in the current folder and execute its tasks.


.. code-block:: console

  $ doit
  .  hello

On the output it displays which tasks were executed. In this case the `dodo` file has only one task, `hello`.

Actions
--------

Every *task* must define **actions**. It can optionally defines other attributes like `targets`, `file_dep`, `verbosity`, `doc` ...

Actions define what the task actually do. A task can define any number of actions. The action "result" is used to determine if task execution was successful or not.

There 2 kinds of `actions`: *cmd-action* and *python-action*.

cmd-action
^^^^^^^^^^^

If `action` is a string it will be executed by the shell.

The result of the task follows the shell convention. If the process exits with the value `0` it is successful.  Any other value means the task failed.

python-action
^^^^^^^^^^^^^^

If `action` is a python callable or a tuple `(callable, *args, **kwargs)` - only `callable` is required. ``args`` is a sequence and  ``kwargs`` is a dictionary that will be used as positional and keywords arguments for the callable. see `Keyword Arguments <http://docs.python.org/tutorial/controlflow.html#keyword-arguments>`_.

The result of the task is given by the returned value of the ``action`` function. So it must return a *boolean* value `True`, `None`, a dictionary or a string to indicate successful completion of the task. Use `False` to indicate task failed. If it raises an exception, it will be considered an error. If it returns any other type it will also be considered an error but this behavior might change in future versions.


example
^^^^^^^^

It is easy to include dynamic (on-the-fly) behavior to your tasks with python code from the `dodo` file. Let's take a look at another example:

.. literalinclude:: tutorial/tutorial_02.py

The function `task_hello` is a *task generator*, not the task itself. The body of the task generator function is always executed when the dodo file is loaded.

.. note::
 The body of task generators are executed even if the task is not going to be executed. So in this example the line `msg = 3 * "hi! "` will always be executed. The body of task generators should be used to create task metadata only, not execute tasks! From now on when it said that a *task* is executed, read the task's actions are executed.


sub-tasks
---------

Most of the time we want to apply the same task several times in different contexts.

The task function can return a python-generator that yields dictionaries. Since each sub-task must be uniquely identified it requires an additional field ``name``.

.. literalinclude:: tutorial/subtasks.py


.. code-block:: console

    $ doit
    .  create_file:file0.txt
    .  create_file:file1.txt
    .  create_file:file2.txt


.. _task-selection:

Task selection
----------------


By default all tasks are executed in the same order as they were defined (the order may change to satisfy dependencies). You can control which tasks will run in 2 ways.

Another example

.. literalinclude:: tutorial/selecttasks.py

DOIT_CONFIG -> default_tasks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*dodo* file defines a dictionary ``DOIT_CONFIG`` with ``default_tasks``, a list of strings where each element is a task name. In the example above we don't want to "install" by default.

.. code-block:: console

    $ doit
    .  t1
    .  t3

Note that the only the task *t3* was specified to be executed. But its dependencies include a target of another task. So those tasks were automatically executed also.


command line selection
^^^^^^^^^^^^^^^^^^^^^^^

From the command line you can control which tasks are going to be execute by passing its task name. Any number of tasks can be passed as positional arguments.

.. code-block:: console

    $ doit t2
    .  t2


You can also specify which task to execute by its target:

.. code-block:: console

    $ doit task1
    .  t1


sub-task selection
^^^^^^^^^^^^^^^^^^^^^

You can select sub-tasks from the command line specifying its full name.

.. literalinclude:: tutorial/subtasks.py


.. code-block:: console

    $ doit create_file:file2.txt
    .  create_file:file2.txt


wildcard selection
^^^^^^^^^^^^^^^^^^^^

You can also select tasks to be executed using a `glob <http://docs.python.org/library/glob.html>`_ like syntax (it must contais a ``*``).

.. code-block:: console

    $ doit create_file:file*
    .  create_file:file1.txt
    .  create_file:file2.txt
    .  create_file:file3.txt


command line variables (*doit.get_var*)
-----------------------------------------

It is possible to pass variable values to be used in dodo.py from the command line.

.. literalinclude:: tutorial/get_var.py

.. code-block:: console

    $ doit
    .  echo
    hi {abc: NO}
    $ doit abc=xyz x=3
    .  echo
    hi {abc: xyz}



private/hidden tasks
---------------------

If task name starts with an underscore '_', it will not be included in the output.

