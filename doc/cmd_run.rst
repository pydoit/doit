==============================
Command line interface - run
==============================

A general `doit` command goes like this:

.. code-block:: console

    $ doit [run] [<options>] [<task|target> <task_options>]* [<variables>]


The `doit` command line contains several sub-commands. Most of the time you just
want to execute your tasks, that's what *run* does. Since it is by far the most
common operation it is also the default, so if you don't specify any sub-command
to *doit* it will execute *run*. So ``$ doit`` and ``$ doit run`` do the same
thing.

The basics of task selection were introduced in :ref:`Task Selection
<task-selection>`.


`python -m doit`
-----------------

`doit` can also be executed without using the `doit` script.

.. code-block:: console

   $ python -m doit

This is specially useful when testing `doit` with different python versions.


dodo file
----------

By default all commands are relative to ``dodo.py`` in the current folder.
You can specify a different *dodo* file containing task with the flag ``-f``.
This flag is valid for all sub-commands.


.. code-block:: console

    $ doit -f release.py


*doit* can seek for the ``dodo.py`` file on parent folders if the option
``--seek-file`` is specified.


as an executable file
-----------------------

using a hashbang
^^^^^^^^^^^^^^^^^^^^^

If you have `doit` installed on ``/usr/bin`` use the following hashbang:

.. code-block:: bash

   #! /usr/bin/doit -f



using the API
^^^^^^^^^^^^^^

It is possible to make a ``dodo`` file become an executable on its own
by calling the ``doit.run()``, you need to pass the ``globals``:


.. literalinclude:: samples/executable.py

.. note::

  The ``doit.run()`` method will call ``sys.exit()`` so any code after it
  will not be executed.


``doit.run()`` parameter will be passed to a :ref:`ModuleTaskLoader <ModuleTaskLoader>` to find your tasks.


from IPython
------------------

You can install and use the `%doit` magic function to load tasks defined
directly in IPython's global namespace (:ref:`more <tools.IPython>`).


returned value
------------------

``doit`` process returns:

 * 0 => all tasks executed successfully
 * 1 => task failed
 * 2 => error executing task
 * 3 => error before task execution starts
        (in this case the reporter is not used)


DB backend
--------------

`doit` saves the results of your tasks runs in a "DB-file", it supports
different backends:

 - `dbm`: (default) It uses `python dbm module <https://docs.python.org/3/library/dbm.html>`_. The actual DBM used depends on what is available on your machine/platform.

 - `json`: Plain text using a json structure, it is slow but good for debugging.

 - `sqlite3`: Support concurrent access
   (DB is updated only once when process is terminated for better performance).


From the command line you can select the backend using the ``--backend`` option.

It is quite easy to add a new backend for any key-value store.


.. warning:

   `dbm` modules do not support concurrent access through different processes.
   `dbm.dumb` will even cause file corruption!


DB-file
----------

Option ``--db-file`` sets the name of the file to save the "DB",
default is ``.doit.db``.
Note that DBM backends might save more than one file, in this case
the specified name is used as a base name.

To configure in a `dodo` file the field name is ``dep_file``

.. code-block:: python

    DOIT_CONFIG = {
        'backend': 'json',
        'dep_file': 'doit-db.json',
    }


.. _verbosity_option:

verbosity
-----------

Option to change the default global task :ref:`verbosity<verbosity>` value.

.. code-block:: console

    $ doit --verbosity 2


failure-verbosity
-----------------

Option to control if stdout/stderr should be re-displayed in the end of
of report. This is useful when used in conjunction with `--continue` option.

.. code-block:: console

    $ doit --failure-verbosity 1


output buffering
----------------

The output (`stdout` and `stderr`) is by default line-buffered
for `CmdAction`. You can change that by specifying the `buffering`
parameter when creating a `CmdAction`. The value zero (the default)
means line-buffered, positive integers are the number of bytes to
be read per call.

Note this controls the buffering from the `doit` process and the
terminal, not to be confused with subprocess.Popen `buffered`.


.. code-block:: python

   from doit.action import CmdAction

   def task_progress():
      return {
        'actions': [CmdAction("progress_bar", buffering=1)],
   }




dir (cwd)
-----------

By default the directory of the `dodo` file is used as the
"current working directory" on python execution.
You can specify a different *cwd* with the *-d*/*--dir* option.

.. code-block:: console

    $ doit --dir path/to/another/cwd

.. note::

   It is possible to get a reference to the original initial
   current working directory (location where the command line
   was executed) using :ref:`initial_workdir`.


continue
---------

By default the execution of tasks is halted on the first task failure or error. You can force it to continue execution with the option --continue/-c

.. code-block:: console

    $ doit --continue


single task execution
----------------------

The option ``-s/--single`` can be used to execute a task without executing
its task dependencies.

.. code-block:: console

    $ doit -s do_something



.. _parallel-execution:

parallel execution
-------------------

`doit` supports parallel execution --process/-n.
This allows different tasks to be run in parallel, as long any dependencies are met.
By default the `multiprocessing <http://docs.python.org/library/multiprocessing.html>`_
module is used.
So the same restrictions also apply to the use of multiprocessing in `doit`.

.. code-block:: console

    $ doit -n 3

You can also execute in parallel using threads by specifying the option
`--parallel-type/-P`.

.. code-block:: console

    $ doit -n 3 -P thread


.. note::

   The actions of a single task are always run sequentially;
   only tasks and sub-tasks are affected by the parallel execution option.

.. warning::

   On Windows, due to some limitations on how `multiprocess` works,
   there are stricter requirements for task properties being picklable than
   other platforms.


.. _reporter:

reporter
---------

`doit` provides different "*reporters*" to display running tasks info
on the console.
Use the option --reporter/-r to choose a reporter.
Apart from the default it also includes:

 * executed-only: Produces zero output if no task is executed
 * json: Output results in JSON format
 * zero: display only error messages (does not display info on tasks
   being executed/skipped). This is used when you only want to see
   the output generated by the tasks execution.

.. code-block:: console

    $ doit --reporter json

.. _custom_reporter:

custom reporter
-----------------

It is possible to define your own custom reporter. Check the code on
`doit/reporter.py
<https://github.com/pydoit/doit/blob/master/doit/reporter.py>`_ ... It is easy
to get started by sub-classing the default reporter as shown below. The custom
reporter can be enabled directly on DOIT_CONFIG dict.

.. literalinclude:: samples/custom_reporter.py

It is also possible distribute/use a custom reporter
as a :ref:`plugin <plugin_reporter>`.

Note that the ``reporter`` have no control over the *real time* output
from a task while it is being executed,
this is controlled by the ``verbosity`` param.


check_file_uptodate
-------------------

`doit` provides different options to check if dependency files are up to date
(see :ref:`file-dep`).  Use the option ``--check_file_uptodate`` to choose:

 * `md5`: use the md5sum.
 * `timestamp`: use the timestamp.

.. note::

   The `timestamp` checker considers a file is not up-to-date if there is
   **any** change in the the modified time (`mtime`), it does not matter if
   the new time is in the future or past of the original timestamp.


You can set this option from command line, but you probably want to set it for
all commands using `DOIT_CONFIG`.

.. code-block:: console

    DOIT_CONFIG = {'check_file_uptodate': 'timestamp'}




custom check_file_uptodate
^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to define your own custom up to date checker. Check the code on
`doit/dependency.py
<https://github.com/pydoit/doit/blob/master/doit/dependency.py>`_ ...
Sub-class ``FileChangedChecker`` and define the 2 required methods as shown
below. The custom checker must be configured using DOIT_CONFIG dict.

.. code-block:: python

    from doit.dependency import FileChangedChecker

    class MyChecker(FileChangedChecker):
        """With this checker, files are always out of date."""
        def check_modified(self, file_path, file_stat, state):
            return True
        def get_state(self, dep, current_state):
            pass

    DOIT_CONFIG = {'check_file_uptodate': MyChecker}


output-file
------------

The option --output-file/-o let you output the result to a file.

.. code-block:: console

    $ doit --output-file result.txt


pdb
-------

If the option ``--pdb`` is used, a post-mortem debugger will be launched in case
of a unhandled exception while loading tasks.


.. _initial_workdir:

get_initial_workdir()
---------------------

When `doit` executes by default it will use the location of `dodo.py`
as the current working directory (unless --dir is specified).
The value of `doit.get_initial_workdir()` will contain the path
from where `doit` was invoked from.

This can be used for example set which tasks will be executed:

.. literalinclude:: samples/initial_workdir.py


minversion
-------------

`minversion` can be used to specify the minimum/oldest `doit` version
that can be used with a `dodo.py` file.

For example if your `dodo.py` makes use of a feature added at `doit X`
and distribute it. If another user who tries this `dodo.py` with a version
older that `X`, doit will display an error warning the user to update `doit`.

`minversion` can be specified as a string or a 3-element tuple with integer
values. If specified as a string any part that is not a number i.e.(dev0, a2,
b4) will be converted to -1.

.. code-block:: console

    DOIT_CONFIG = {
        'minversion': '0.24.0',
    }


.. note::

  This feature was added on `doit` 0.24.0.
  Older Versions will not check or display error messages.


.. _auto-delayed-regex:

automatic regex for delayed task loaders
------------------------------------------

When specifying a target for `doit run`, *doit* usually only considers usual
tasks and :ref:`delayed tasks <delayed-task-creation>` which have a target
regex specified. Any task generated by a delayed task loader which has
:ref:`no target regex specified <specify-target-regex>` will not be
considered.

By specifying `--auto-delayed-regex`, every delayed task loader having no
target regex specified is assumed to have `.*` specified, a regex which
matches any target.
