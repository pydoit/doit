============
Command run
============

Most of the time you just want to execute your tasks that's what *run* does. Since it is by far the most common operation it is also the default, so if you don't specify any sub-command to *doit* it will *run*. So ``$ doit`` and ``$ doit run`` are the same thing.


dodo file
----------

By default all commands are relative to ``dodo.py`` in the current folder. You can specify a different *dodo* file containing task with the flag ``-f``. (This is valid for all sub-commands)


.. code-block:: console

    eduardo@eduardo:~$ doit -f release.py



verbosity
-----------

By default the stdout from a task is captured and its stderr is sent to the console. If the task fails or there is an error the stdout and a traceback (if any) is displayed.

There are 3 levels of verbosity:

0:
  capture (do not print) stdout/stderr from task.

1 (default):
  capture stdout only.

2:
  do not capture anything (print everything immediately).


You can control the verbosity by:

* --verbosity/-v command line option.

  change verbosity of all executed tasks.

.. code-block:: console

    eduardo@eduardo:~$ doit --verbosity 2

* task attribute verbosity

.. literalinclude:: tutorial/verbosity.py

.. code-block:: console

    eduardo@eduardo:~$ doit
    .  print
    hello


Task selection
----------------


By default all tasks are executed in the same order as they were defined (the order may change to satisfy dependencies). You can control which tasks will run in 2 ways.

Another example

.. literalinclude:: tutorial/selecttasks.py

DEFAULT_TASKS
^^^^^^^^^^^^^^

*dodo* file defines a variable ``DEFAULT_TASKS``. A list of strings where each element is a task name. In the example above we don't want to "install" by default.

.. code-block:: console

    eduardo@eduardo:~$ doit
    .  t1
    .  t3

Note that the only the task *t3* was specified to be executed. But its dependencies include a target of another task. So those tasks were automatically executed also.


command line selection
^^^^^^^^^^^^^^^^^^^^^^^

From the command line you can control which tasks are going to be execute by passing its task name.

.. code-block:: console

    eduardo@eduardo:~$ doit t2
    .  t2


You can also specify which task to execute by its target:

.. code-block:: console

    eduardo@eduardo:~$ doit task1
    .  t1


parameters
-----------

It is possible to pass option parameters to the task through the command line.

Just a add a 'params' fiels to the task dictionary. `params` must be a list of dictionaries where every entry is an option parameter. Each parameter must define a name, and a default value. It can optionally define a "short" and "long" names to be used from the command line (it follows unix command line conventions). It may also specify a type the parameter should be converted to.

See the example:

.. literalinclude:: tutorial/parameters.py


For python-actions the python function must define arguments with the same name as a task parameter.

.. code-block:: console

    eduardo@eduardo:~$ doit py_params -p abc --param2 4
    .  py_params
    abc
    9

For cmd-actions use python string substitution notation:

.. code-block:: console

    eduardo@eduardo:~$ doit cmd_params -f "-c --other value"
    .  cmd_params
    mycmd -c --other value xxx


title
-------

By default when you run `doit` only the task name is printed out on the output. You can customize the output passing a "title" function to the task:

.. literalinclude:: tutorial/title.py

.. code-block:: console

    eduardo@eduardo:~$ doit
    .  executing... Cmd: echo abc efg


dir (cwd)
-----------

By default relative paths of file used on the `dodo` file and the "current working directory" used on python execution is the same as the location of the `dodo` file. You can specify a different *cwd* with the --dir/-d option.

.. code-block:: console

    eduardo@eduardo:~$ doit --dir


continue
---------

By default the execution of tasks is halted on the first task failure or error. You can force it to continue execution with the option --continue/-c

.. code-block:: console

    eduardo@eduardo:~$ doit --continue


reporter
---------

`doit` provides different "reporters" when running tasks. Use the option --reporter/-r Apart from the default it also includes:

 * executed-only: Produces zero output unless a task is executed
 * json: Output results in JSON format

.. code-block:: console

    eduardo@eduardo:~$ doit --reporter json

output-file
------------

The option --output-file/-o let you output the result to a file.

.. code-block:: console

    eduardo@eduardo:~$ doit --output-file result.txt
