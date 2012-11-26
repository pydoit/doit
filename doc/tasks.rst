========
Tasks
========

Intro
-------

`doit` is all about automating task dependency management and execution. Tasks can execute external shell commands/scripts or python functions (actually any callable). So a task can be anything you can code :)

Tasks are defined using `python <http://python.org/>`_, in a plain python file with some conventions. A function that starts with the name `task_` defines a *task-creator* recognized by `doit`. These functions must return (or yield) dictionaries representing a *task*. A python module/file that defines *tasks* for `doit` is called **dodo** file (that is something like a `Makefile` for `make`).

.. note::

    You should be comfortable with python basics. If you don't know python yet check `Python tutorial <http://docs.python.org/tut/>`_.


Take a look at this example (file dodo.py):

.. literalinclude:: tutorial/hello.py

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

If `action` is a python callable or a tuple `(callable, *args, **kwargs)` - only
`callable` is required. The callable must be a funcion, method or callable
object. Classes and built-in funcions are not allowed. ``args`` is a sequence
and ``kwargs`` is a dictionary that will be used as positional and keywords
arguments for the callable.
see `Keyword Arguments <http://docs.python.org/tutorial/controlflow.html#keyword-arguments>`_.


The result of the task is given by the returned value of the ``action`` function. So it must return a *boolean* value `True`, `None`, a dictionary or a string to indicate successful completion of the task. Use `False` to indicate task failed. If it raises an exception, it will be considered an error. If it returns any other type it will also be considered an error but this behavior might change in future versions.


example
^^^^^^^^

It is easy to include dynamic (on-the-fly) behavior to your tasks with python code from the `dodo` file. Let's take a look at another example:

.. literalinclude:: tutorial/tutorial_02.py

The function `task_hello` is a *task-creator*, not the task itself. The body of the task-creator function is always executed when the dodo file is loaded.

.. note::
 The body of task-creators are executed even if the task is not going to be executed. So in this example the line `msg = 3 * "hi! "` will always be executed. The body of task-creators should be used to create task metadata only, not execute tasks! From now on when it said that a *task* is executed, read the task's actions are executed.


task name
------------

By default a task name is taken from the name of the python function
that generates the task.
For example a `def task_hello` would create a task named ``hello``.

It is possible to explicit set a task name with the parameter ``basename``.

.. literalinclude:: tutorial/task_name.py


.. code-block:: console

  $ doit
  .  hello
  .  hello2


When explicit using ``basename`` the task-creator is not limited
to create only one task.
Using ``yield`` it can generate several tasks at once.
It is also possible to ``yield`` a generator that genrate tasks.
This is useful to write some generic/reusable task-creators.

.. literalinclude:: tutorial/task_reusable.py

.. code-block:: console

  $ doit
  .  t2
  .  t1



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


Dependencies & Targets
-------------------------

One of the main ideas of `doit` (and other build-tools) is to check if the
tasks/targets are **up-to-date**. In case there is no modification in the
dependencies and the targets already exist, it skips the task execution to
save time, as it would produce the same output from the previous run.

Dependency
  A dependency indicates an input to the task execution.

Target
  A *target* is the result/output file produced by the task execution.


i.e. In a compilation task the source file is a *file_dep*,
the object file is a *target*.

.. literalinclude:: tutorial/compile.py


`doit` automatically keeps track of file dependencies. It saves the
signature (MD5) of the dependencies every time the task is completed successfully.

So if there are no modifications to the dependencies and you run `doit` again.
The execution of the task's actions is skipped.


.. code-block:: console

  $ doit
  .  compile
  $ doit
  -- compile

Note the ``--`` (2 dashes, one space) on the command output on the second
time it is executed. It means, this task was up-to-date and not executed.


file_dep (file dependency)
-----------------------------

Different from most build-tools dependencies are on tasks, not on targets.
So `doit` can take advantage of the "execute only if not up-to-date" feature
even for tasks that not define targets.

Lets say you work with a dynamic language (python in this example).
You don't need to compile anything but you probably wants to apply a lint-like
tool (i.e. `pyflakes <http://pypi.python.org/pypi/pyflakes>`_) to your
source code files. You can define the source code as a dependency to the task.


.. literalinclude:: tutorial/checker.py

.. code-block:: console

   $ doit
   .  checker
   $ doit
   -- checker

Note the ``--`` again to indicate the execution was skipped.

Traditional build-tools can only handle files as "dependencies".
`doit` has several ways to check for dependencies, those will be introduced later.


targets
-------

Targets can be any file path (a file or folder). If a target doesn't exist
the task will be executed. There is no limitation on the number of targets
a task may define. Two different tasks can not have the same target.

Lets take the compilation example again.

.. literalinclude:: tutorial/compile.py

* If there are no changes in the dependency the task execution is skipped.
* But if the target is removed the task is executed again.
* But only if does not exist. If the target is modified but the dependencies
  do not change the task is not executed again.

.. code-block:: console

    $ doit
    .  compile
    $ doit
    -- compile
    $ rm main.o
    $ doit
    .  compile
    $ echo xxx > main.o
    $ doit
    -- compile


execution order
-----------------

If your tasks interact in a way where the target (output) of one task is a
file_dep (input) of another task, `doit` will make sure your tasks are
executed in the correct order.

.. literalinclude:: tutorial/taskorder.py

.. code-block:: console

  $ doit
  .  create
  .  modify



.. _task-selection:

Task selection
----------------


By default all tasks are executed in the same order as they were defined (the order may change to satisfy dependencies). You can control which tasks will run in 2 ways.

Another example

.. literalinclude:: tutorial/selecttasks.py

DOIT_CONFIG -> default_tasks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*dodo* file defines a dictionary ``DOIT_CONFIG`` with ``default_tasks``, a list of strings where each element is a task name.

.. code-block:: console

    $ doit
    .  t1
    .  t3

Note that only the task *t3* was specified to be executed by default.
But its dependencies include a target of another task (t1).
So that task was automatically executed also.


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

