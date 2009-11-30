=====
Intro
=====

`doit` is all about automating the execution of tasks. Tasks can execute external shell commands/scripts or python functions (actually any callable). So a task can be anything you can code :)

Tasks are defined using `python <http://python.org/>`_, in a plain python file with some conventions. A function that starts with the name `task_` defines a *task generator* recognized by `doit`. These functions must return (or yield) dictionaries representing a *task*. A python module/file that defines *tasks* for `doit` is called **dodo** file (that is something like a `Makefile` for `make`).

.. note::

    You should be comfortable with python basics. If you don't know python yet check `Python tutorial <http://docs.python.org/tut/>`_ and `Dive Into Python <http://www.diveintopython.org/>`_.


Take a look at this example (file dodo.py):

.. literalinclude:: tutorial/tutorial_01.py

When `doit` is executed without any parameters it will look for tasks in a file named `dodo.py` in the current folder and execute its tasks.


.. code-block:: console

  eduardo@eduardo~$ doit
  hello

On the output it displays which tasks were executed. In this case the `dodo` file has only on task, `hello`.
