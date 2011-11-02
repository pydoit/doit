============
Command run
============

Most of the time you just want to execute your tasks, that's what *run* does. Since it is by far the most common operation it is also the default, so if you don't specify any sub-command to *doit* it will *run*. So ``$ doit`` and ``$ doit run`` are the same thing.

The basics of task selection were introduced in :ref:`Task Selection <task-selection>`.


dodo file
----------

By default all commands are relative to ``dodo.py`` in the current folder. You can specify a different *dodo* file containing task with the flag ``-f``. (This is valid for all sub-commands)


.. code-block:: console

    $ doit -f release.py


*doit* can seek for the ``dodo.py`` file on parent folders if the the option ``--seek-file`` is specified.


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

    $ doit --verbosity 2

* task attribute verbosity

.. literalinclude:: tutorial/verbosity.py

.. code-block:: console

    $ doit
    .  print
    hello


parameters
-----------

It is possible to pass option parameters to the task through the command line.

Just a add a 'params' fiels to the task dictionary. `params` must be a list of dictionaries where every entry is an option parameter. Each parameter must define a name, and a default value. It can optionally define a "short" and "long" names to be used from the command line (it follows unix command line conventions). It may also specify a type the parameter should be converted to.

See the example:

.. literalinclude:: tutorial/parameters.py


For python-actions the python function must define arguments with the same name as a task parameter.

.. code-block:: console

    $ doit py_params -p abc --param2 4
    .  py_params
    abc
    9

For cmd-actions use python string substitution notation:

.. code-block:: console

    $ doit cmd_params -f "-c --other value"
    .  cmd_params
    mycmd -c --other value xxx


title
-------

By default when you run `doit` only the task name is printed out on the output. You can customize the output passing a "title" function to the task:

.. literalinclude:: tutorial/title.py

.. code-block:: console

    $ doit
    .  executing... Cmd: echo abc efg


dir (cwd)
-----------

By default relative paths of file used on the `dodo` file and the "current working directory" used on python execution is the same as the location of the `dodo` file. You can specify a different *cwd* with the --dir/-d option.

.. code-block:: console

    $ doit --dir path/to/another/cwd


continue
---------

By default the execution of tasks is halted on the first task failure or error. You can force it to continue execution with the option --continue/-c

.. code-block:: console

    $ doit --continue



parallel execution
-------------------

`doit` supports parallel execution (using multiple processes) --process/-n. The `multiprocessing <http://docs.python.org/library/multiprocessing.html>`_ module is used. So the same restrictions also apply to the use of multiprocessing in `doit`.

.. code-block:: console

    $ doit -n 3



reporter
---------

`doit` provides different "reporters" to display running tasks info on the console. Use the option --reporter/-r to choose a reporter. Apart from the default it also includes:

 * executed-only: Produces zero output if no task is executed
 * json: Output results in JSON format

.. code-block:: console

    $ doit --reporter json


custom reporter
-----------------

It is possible to define your own custom reporter. Check the code on doit/reorter.py... It is easy to get started by sub-classing the default reporter as shown below. The custom reporter must be configured using DOIT_CONFIG dict.

.. literalinclude:: tutorial/custom_reporter.py



output-file
------------

The option --output-file/-o let you output the result to a file.

.. code-block:: console

    $ doit --output-file result.txt


config
--------

Command line parameters can be set straight on a `dodo` file. This example below sets the default tasks to be run, the `continue` option, and a different reporter.

.. literalinclude:: tutorial/doit_config.py

So if you just execute

.. code-block:: console

   $ doit

it will have the same effect as executing

.. code-block:: console

   $ doit --continue --reporter json my_task_1 my_task_2

You need to check `doit_cmd.py <http://bazaar.launchpad.net/~schettino72/doit/trunk/annotate/head%3A/doit/doit_cmd.py>`_ to find out how parameter maps to config names.

.. note::

  The parameters `--file` and `--dir` can not be used on config because they control how the dodo file itself is loaded.


bash completion
-----------------

Bash completion for `doit` to auto-complete task names is available at `bash_completion_doit <http://bazaar.launchpad.net/~schettino72/doit/trunk/annotate/head%3A/bash_completion_doit>`_ . To activate it:

.. code-block:: console

  $ source <path-to-file>/bash_completion_doit

