============
Command run
============

By default all commands are relative to ``dodo.py`` in the current folder. You can specify a different *dodo* file containing task with the flag ``-f``. (This is valid for all sub-commands)

Most of the time you just want to execute your tasks that's what *run* does. Since it is by far the most common operation it is also the default, so if you don't specify any sub-command to *doit* it will *run*. So ``$ doit`` and ``$ doit run`` are the same thing.

By default all tasks are executed in the same order as they were defined (the order may change to satisfy dependencies). You can control which tasks will run in 2 ways.

Another example
.. literalinclude:: tutorial/select.py

DEFAULT_TASKS
--------------

*dodo* file defines a variable ``DEFAULT_TASKS``. A list of strings where each element is a task name. In the example above we don't want to "install" by default.

.. code-block:: console

    eduardo@eduardo:~$ doit
    compile:main => Cmd: cc -c main.c
    compile:command => Cmd: cc -c command.c
    compile:kbd => Cmd: cc -c kbd.c
    link => Cmd: cc -o edit main.o command.o kbd.o

Note that the only the task *link* was specified to be executed. But its dependencies include targets from other tasks. So those tasks were automatically executed also.

selecting tasks
-----------------

From the command line you can control which tasks are going to be execute by passing its task name.

.. code-block:: console

    eduardo@eduardo:~$ doit compile:main
    compile:main => Cmd: cc -c main.c

Note how you can execute only a sub-task using a colon ``:`` to separate the task name from the sub-task name.


You can also specify which task to execute by its target:

.. code-block:: console

    eduardo@eduardo:~$ doit main.o
    compile:main => Cmd: cc -c main.c



parameters
-----------



title
-------

By default when you run `doit` only the task name is printed out on the output. You can customize the output passing a "title" function to the task::


verbosity
-----------

dir (cwd)
-----------

continue
---------

reporter
---------

outfile
--------
