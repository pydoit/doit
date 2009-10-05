================
The Command Line
================

Lets use more complex example to demonstrate the command line features. The example below is used to manage a very simple C project.


.. literalinclude:: tutorial/cproject.py


`doit` comes with several commands. `doit help` will list all available commands. You can also get help from each available command. e.g. `doit help run`.

By default all commands are relative to ``dodo.py`` in the current folder. You can specify a different *dodo* file containing task with the flag ``-f``.



list
------

*list* is used to show all tasks available in a *dodo* file.

.. code-block:: console

   eduardo@eduardo:~$ doit list
   link : create binary program
   compile : compile C files
   install : install executable (TODO)


The task description is taken from the first line of task function docstring. You can also set it using the *doc* attribute on the task dictionary.


run
-----

Of course most of the time you just want to execute your tasks thats what *run* does. Since it is by far the most common operation it is also the default, so if you dont specify any sub-command to *doit* it will *run*. So ``$ doit`` and ``$ doit run`` are the same thing.

By default all tasks are executed in the same order as they were defined (the order may change to satisfy dependencies). You can control which tasks will run in 2 ways.


DEFAULT_TASKS
^^^^^^^^^^^^^^

*dodo* file defines a variable ``DEFAULT_TASKS``. A list of strings where each element is a task name. In the example above we dont want to "install" by default.

.. code-block:: console

    eduardo@eduardo:~$ doit
    compile:main => Cmd: cc -c main.c
    compile:command => Cmd: cc -c command.c
    compile:kbd => Cmd: cc -c kbd.c
    link => Cmd: cc -o edit main.o command.o kbd.o

Note that the only the task *link* was specified to be executed. But its dependencies include targets from other tasks. So those tasks were automatically executed also.

command line
^^^^^^^^^^^^

From the command line you can control which tasks are going to be execute by passing its task name.

.. code-block:: console

    eduardo@eduardo:~$ doit compile:main
    compile:main => Cmd: cc -c main.c

Note how you can excute only a subtask using a colon ``:`` to separate the task name from the sub-task name.


You can also specify which task to execute by its target:

.. code-block:: console

    eduardo@eduardo:~$ doit main.o
    compile:main => Cmd: cc -c main.c


forget
-------


Suppose you change the compilation parameters in the compile action. *doit* will think your task is up-to-date but actually it is not. In this case you can use the *forget* command to make sure the given task will be executed again even with no changes in the dependencies.

If you do not specify any task, all tasks are "*forget*".

.. code-block:: console

    eduardo@eduardo:~$ doit forget

.. note::

  *doit* keeps track of which tasks are successful in the file ``.doit.db``. This file uses JSON.

clean
------

A common scenario is a task that needs to revert its actions. A task may include a *clean* attribute. This attribute can be ``True`` to remove all of its target files. Or it could be a list of actions, again action could be a string with a shell comamnd or a tuple with a python callable.

You can specify which task to *clean* or *clean* if no task is specified.

.. code-block:: console

    eduardo@eduardo:~$ doit clean


