================
Other Commands
================

Lets use more complex example to demonstrate the command line features. The example below is used to manage a very simple C project.


.. literalinclude:: tutorial/cproject.py



help
-------

`doit` comes with several commands. `doit help` will list all available commands.

You can also get help from each available command. e.g. `doit help run`.

`doit help task` will display information on all fields/attributes a task dictionary from a `dodo` file accepts.


.. _cmd-list:

list
------

*list* is used to show all tasks available in a *dodo* file.

.. code-block:: console

   $ doit list
   link : create binary program
   compile : compile C files
   install : install executable (TODO)


By default task name and description are listed. The task description is taken from the first line of task function doc-string. You can also set it using the *doc* attribute on the task dictionary. It is possible to ommit the description using the option *-q*/*--quiet*.

By default sub-tasks are not listed. It can list sub-tasks using the option *--all*.

By default task names that start with an underscore(*_*) are not listed. They are listed if the option *-p*/*--private* is used.

Task status can be printed using the option *-s*/*--status*.

Task's file-dependencies can be printed using the option *--deps*.



forget
-------


Suppose you change the compilation parameters in the compile action. Or you changed the code from a python-action. *doit* will think your task is up-to-date based on  the dependencies but actually it is not! In this case you can use the *forget* command to make sure the given task will be executed again even with no changes in the dependencies.

If you do not specify any task, the default tasks are "*forget*".

.. code-block:: console

    $ doit forget

.. note::

  *doit* keeps track of which tasks are successful in the file ``.doit.db``.



clean
------

A common scenario is a task that needs to "revert" its actions. A task may include a *clean* attribute. This attribute can be ``True`` to remove all of its target files. If there is a folder as a target it will be removed if the folder is empty, otherwise it will display a warning message.

The *clean* attribute can be a list of actions, again, an action could be a string with a shell command or a tuple with a python callable.

You can specify which task to *clean*. If no task is specified the clean operation of default tasks are executed.

.. code-block:: console

    $ doit clean


By default if a task contains task-dependencies those are not automatically
cleaned too. You can enable this using the option *-c*/*--clean-dep*.
If you are executing the default tasks this flag is automatically set.


.. note::

    By default only the default tasks' clean are executed, not from all tasks.
    You can clean all tasks using the *-a*/*--all* argument.

If you want check which tasks the clean operation would affect you can use the option *-n*/*--dry-run*.



ignore
-------

It is possible to set a task to be ignored/skipped (that is not executed). This is useful for example when you are performing checks in several files and you want to skip the check in some of them temporarily.

.. literalinclude:: tutorial/subtasks.py


.. code-block:: console

    $ doit
    .  create_file:file0.txt
    .  create_file:file1.txt
    .  create_file:file2.txt
    $ doit ignore create_file:file1.txt
    ignoring create_file:file1.txt
    $ doit
    .  create_file:file0.txt
    !! create_file:file1.txt
    .  create_file:file2.txt

Note the ``!!``, it means that task was ignored. To reverse the `ignore` use `forget` sub-command.



.. _cmd-auto:

auto (watch)
-------------

.. note::

   Supported on Linux and Mac only.

`auto` sub-command is an alternative way of executing your tasks. It is a long running process that only terminates when it is interrupted (Ctrl-C). When started it will execute the given tasks. After that it will watch the file system for modifications in the file-dependencies.  When a file is modified the tasks are re-executed.


.. code-block:: console

    $ doit auto


.. note::

   The `dodo` file is actually re-loaded/executed in a separate procees
   everytime tasks need to be re-executed.



dumpdb
--------

`doit` saves internal data in a file (`.doit.db` be default).
It uses a binary format (whatever python's dbm is using in your system).
This command will simply dumps its content in readable text format in the output.

.. code-block:: console

    $ doit dumpdb



strace
--------

This command uses `strace <https://en.wikipedia.org/wiki/Strace>`_
utility to help you verify which files are being used by a given task.

The output is a list of files prefixed with `R` for open in read mode
or `W` for open in write mode.
The files are listed in chronological order.

This is a debugging feature wiht many lilmitations.
  * can strace only one task at a time
  * can only strace CmdAction
  * the process being traced itself might have some kind of cache,
    that means it might not write a target file if it exist
  * does not handle chdir

So this is NOT 100% reliable, use with care!

.. code-block:: console

    $ doit strace <task-name>
