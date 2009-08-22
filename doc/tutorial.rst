========
Tutorial
========

Tasks
=====

`doit` is all about automating tasks execution. Tasks can be external shell commands/scripts or a python function (or any callable). So a task can be anything you can code :)

`doit` will execute tasks defined in a configuration file, something like a Makefile here called "dodo" file. They are written in python.

You should be comfortable with python basics. If you don't know python yet check `Python tutorial <http://docs.python.org/tut/>`_ and `Dive Into Python <http://www.diveintopython.org/>`_.

The first example we will just create a file with the content "Hello World". Using both a python-task and a cmd-task.

``tutorial_01.py``:

.. literalinclude:: tutorial/tutorial_01.py

`doit` will read the configuration file and collect the defined tasks. Any function that start with the string ``task_`` is a task generator. These functions must return a dictionary where it specifies the task parameters. The only required parameter is ``action``.

Cmd-Task
  If ``action`` is a string it will be executed by the shell.
  The result of the task follows the shell convention. If the process exits with the value ``0`` it is successful.  Any other value means the task failed.
  It also support a list of commands. It must be passed as a list of strings where each string is a shell command.

Python-Task
  If ``action`` is a function reference (or any callable) the python function is executed.
  The result of the task is given by the returned value of the ``action`` function. So it **must** return a value that evaluates to True to indicate successful completion of the task.

Group-Task
  If ``action`` is ``None``. As you might expect this task wont do anything but group tasks together. It will be explained later.

After executing the command below you should get the two files with the "Hello World" text.

::

  $ doit -f tutorial_01.py
  hello_python => Python: function say_hello
  hello_sh => Cmd: echo 'Hello World' > hello_sh.txt


Task Results
============

`doit` classify the task result as success, failure or error.

Failures are caused by the task not being completed successfully. For python-task when the returned value is False. For a cmd-task when the returned value by the process is bigger than 125.

Errors are caused by unexpected problems in the execution of a task. For a python-task an exception is raised. For a cmd-task returns a value between 1 and 125.

So it basically means that an error is caused by the definition of the task. And a failure is caused by the task itself.

The return codes for cmd-task are defined based on http://www.gnu.org/software/bash/manual/bashref.html#Exit-Status. But not all applications follow this convention.


Task arguments
==============

You can pass arguments to your Python-Task *action* function using the optional fields ``args`` (sequence) and ``kwargs`` (dictionary). They will be passed as `*args <http://docs.python.org/tut/node6.html#SECTION006730000000000000000>`_ and `**kwargs <http://docs.python.org/tut/node6.html#SECTION006720000000000000000>`_ to the *action* function.

For Cmd-Task, just manipulate the string!

``tutorial_02.py``

.. literalinclude:: tutorial/tutorial_02.py



Dependencies & Targets
======================

Dependency
  A *dependency* indicates that the task depends on it to be executed.

  i.e. A 'C' object file depends on the source code file to execute the compilation.


Target
  A task *target* is the result produced by the task execution.

  i.e. An object file from a compilation task.


``Dependencies`` and ``targets`` are optional fields for a task definition.

`doit` automatically keeps track of file-dependencies. It saves the signature (MD5) of the dependencies every time the task is completed successfully. In case there is no modification in the dependencies and the targets already exist, it skip the task execution to save time as it would produce the same output from the previous run. Tasks without dependencies are always executed.

Dependencies are on tasks not on targets, so a task even without defining targets can take advantage of the execute only if not up-to-date feature.

Targets can be any file path (a file or folder). If a target doesnt exist the task will be executed. If a task defines a target but no dependencies it will always be executed.

There are four kinds of dependencies:

file-dependency:
  type: string. value is the path of the file (relative to the dodo file).

folder-dependency:
  type: string. This is not a dependency on the same way of a file-dependency. It is not checked if the folder was modified or not. It is only a handy way to indicate that a folder should exist before the task is executed. If the folder doesn't exist it is created. If it already exist, nothing happens. folder-depencies are not used to determine if a task is up-to-date or not. So, if a task defines only folder-dependency it will always be executed. The value is the path on the file system (relative to the dodo file). The last charachter of the string must be a '/'. i.e. "path/to/build/"

task-dependency:
  type: string. values is the name of a task preceeded by ':'. i.e. ":compile". task-dependency are only used to force a certain order in the execution of the tasks. task-depencies are not used to determine if a task is up-to-date or not. So if a task only defines task-dependency it will always be executed.

run-once:
  type: boolean. value must always be `True`. This is actually used to say that a task has no dependency but should be executed only once. This is useful if you have a task with no dependency that creates a target and you dont want to create the target over and over again.


Targets can only be a string with a file path.


Example 1 - Simple File Dependency - Lint
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose you want to apply a lint-like tool (`PyChecker <http://pychecker.sourceforge.net/>`_) to your source code file. You can define the source code as a dependency to the task.

``checker.py``

.. literalinclude:: tutorial/checker.py

This way the Pychecker is executed only when source file has changed. On the output the string ``---`` preceding the task description indicates the task execution was skipped because it is up-to-date.

::

  $ doit -f checker.py
  checker => Cmd: pychecker sample.py
  $ doit -f checker.py
  --- checker => Cmd: pychecker sample.py


Example 2 - Target + Folder Dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Targets indicate what will be created by the execution of the task.

#. If you delete a target after a successful run. The task will be executed again even if there are no modifications in the dependencies.

#. In case the target file is a dependency for another file it ensure tasks will be executed on the proper order. (By default tasks are executed in the order they were defined).

In the next example the task "count_lines" is used to create a file reporting the number of lines from "files.txt". "files.txt" is actually the target from another task.

``counter.py``

.. literalinclude:: tutorial/counter.py

::

  $ doit -f counter.py
  ls => Cmd: ls -1 > build/files.txt
  count_lines => Cmd: wc -l build/files.txt > result/count.txt


* Notice that "task_ls" is executed before "task_count_line" even that it was defined after. Because its target is a dependency of "task_count_line".

* ``ls`` will write its output in the ``build`` folder. Since this folder is a "folder-dependency" it is not required to exist before you run `doit`.

* "task_ls" is always executed (because it doesn't define any file-dependency).

* "task_count_lines" is executed only if "files.txt" is change.

Lets execute it one more time. Notice the "---" to indicate the task was not executed.

::

  $ doit -f counter.py
  ls => Cmd: ls -1 > build/files.txt
  --- count_lines => Cmd: wc -l build/files.txt > result/count.txt


Example 3 - Task Dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To define a dependency on another task use the task name (whatever comes after ``task_`` on the function name) preceded by ":". It is used to enforce tasks are executed on the desired order. This example we make sure we include a file with the latest revision number of the bazaar repository on the tar file.

``tar.py``

.. literalinclude:: tutorial/tar.py

::

  $ doit -f tar.py
  version => Cmd: bzr version-info > revision.txt
  tar => Cmd: tar -cf foo.tar *


Example 4 - run-once
^^^^^^^^^^^^^^^^^^^^

Sometimes you might want to have execute a task only once even if it has no dependencies. For example, if you need a package that you dont want to include in your source distribution. Just add ``True`` as a dependency.

``download.py``

.. literalinclude:: tutorial/download.py

This way it will shrinksafe will be downloaded only once. Notice that if delete the target file the task will be executed again (it will download the file again) it means that ensuring that the target exist has precedence over the "run-once" instruction.



Subtasks
========

Most of the time we want to apply the same task several times in different contexts.

The task function can return a python-generator that yields dictionaries. Since each subtask must be uniquely identified it requires an additional field ``name``.

Below an example on how to execute PyChecker for all files in a folder.

``checker2.py``

.. literalinclude:: tutorial/checker2.py


Task Groups
===========

You can define group of tasks by adding tasks as dependencies and setting its action to `None`.

``group.py``

.. literalinclude:: tutorial/group.py

::

  $ doit -f group.py mygroup
  foo => Cmd: echo foo
  bar => Cmd: echo bar
  mygroup => Group: :foo, :bar

Notice that a task is never executed twice in the same "run".


Putting all together
====================

Really. You already learned everything you need to know! Quite easy :)

I am going to show one real life example. Compressing javascript files, and combining them in a single file.

``compressjs.py``

.. literalinclude:: tutorial/compressjs.py

Running::

  $ doit -f compressjs.py

Let's start from the end.

``task_pack_js`` will combine all compressed javascript files into a single file.

``task_shrink_js`` compress a single javascript file and save the result in the "build" folder.

``task_get_shrinksafe`` will download shrinksafe.


The command line
================

`doit` comes with several commands. `doit help` will list all available commands. You can also get help from each available command. e.g. `doit help run`. The basic commands are:

help
  show help / reference

run
  run tasks

list
  list tasks from dodo file

forget
  clear successful run status from DB

template
  create a dodo.py template file


* 'run' is the default command, so if you don't specify any command 'run' will be used.

* Commands that take a dodo file as a parameter will use the file named ``dodo.py`` on the current folder as default. to specify another file containg task. use the file parameter ``-f``.

* ``doit`` creates a file ``.doit.db`` where information of previous runs are saved.
