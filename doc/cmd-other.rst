.. meta::
   :description: doit provides several sub-commands to introspect and manipulated defined tasks
   :keywords: python, doit, documentation, guide, task, list, auto, introspection

.. title:: A survey of doit sub-commands for task manipulation


==================================
sub-commands for task manipulation
==================================

.. note::

    Not all options/arguments are documented below.
    Always check `doit help <cmd>` to see a complete list of options.


Let's use a more complex example to demonstrate the command line features.
The example below is used to manage a very simple C project.


.. literalinclude:: samples/cproject.py



.. _cmd-help:

help
-------

`doit` comes with several commands. `doit help` will list all available commands.

You can also get help from each available command. e.g. `doit help run`.

`doit help task` will display information on all fields/attributes a task dictionary from a `dodo` file accepts.


.. _cmd-list:

list
------

*list* is used to show all tasks available in a *dodo* file.
Tasks are listed in alphabetical order by default, but *--sort=definition* can
be specified to sort them in the order in which they appear in the `dodo` file.

.. code-block:: console

   $ doit list
   compile : compile C files
   install : install executable (TODO)
   link : create binary program


By default task name and description are listed. The task description is taken
from the first line of task function doc-string. You can also set it using the
*doc* attribute on the task dictionary. It is possible to omit the description
using the option *-q*/*--quiet*.

By default sub-tasks are not listed. It can list sub-tasks using the option
*--all*.

By default task names that start with an underscore(*_*) are not listed. They
are listed if the option *-p*/*--private* is used.

Task's file-dependencies can be printed using the option *--deps*.

status
^^^^^^

If you would like to know if a task would actually be executed,
the option *-s*/*--status* can be used to display the task's status .
It is one of:

 - ``R``: run
 - ``U``: up-to-date
 - ``I``: ignored

This is an alternative to *dry-run* or *preflight* feature provided by some tools.


info
----

You can check a task meta-data using the *info* command.
This might be useful when have some complex code generating
the task meta-data.

.. code-block:: console

    $ doit info link

    link

    status  : up-to-date

    file_dep:
      - command.o
      - kbd.o
      - main.o

    targets:
      - edit


Note that if the task is **not** *up-to-date* the reason a task is not up-to-date.

.. code-block:: console

   $ doit info link

   link

   status  : run

    * The following file dependencies have changed:
       - main.o
       - kbd.o
       - command.o


forget
-------


Suppose you change the compilation parameters in the compile action. Or you
changed the code from a python-action. *doit* will think your task is up-to-date
based on the dependencies but actually it is not! In this case you can use the
*forget* command to make sure the given task will be executed again even with no
changes in the dependencies.

If you do not specify any task, the default tasks are "*forget*".

.. code-block:: console

    $ doit forget

.. note::

  *doit* keeps track of which tasks are successful in the file ``.doit.db``.


--disable-default
^^^^^^^^^^^^^^^^^

If your default tasks are expensive, you can avoid accidentally forgetting
all of your default tasks by setting ``forget_disable_default = True`` in ``doit.cfg``.

You can explicitly forget default tasks with ``--enable-default``.

--all
^^^^^

Use ``doit forget --all`` to forget *all* tasks.


clean
------

A common scenario is a task that needs to "revert" its actions. A task may
include a *clean* attribute. This attribute can be ``True`` to remove all of its
target files. If there is a folder as a target it will be removed if the folder
is empty, otherwise it will display a warning message.

.. note::

  The targets' removal order will be the reverse of their lexical ordering.
  This ensures that files in a directory are removed before the directory
  irrespective of their order in the ``targets`` array.

The *clean* attribute can be a list of actions. An action could be a
string with a shell command or a tuple with a python callable.

If you want to clean the targets and add some custom clean actions,
you can include the `doit.task.clean_targets` instead of passing `True`:

.. literalinclude:: samples/clean_mix.py


You can specify which task to *clean*. If no task is specified the clean operation of default tasks are executed.

.. code-block:: console

    $ doit clean


By default if a task contains task-dependencies those are not automatically
cleaned too. You can enable this using the option *-c*/*--clean-dep*.
If you are executing the default tasks this flag is automatically set.


.. note::

    By default only the default tasks' clean are executed, not from all tasks.
    You can clean all tasks using the *-a*/*--all* argument.

If you like to also make doit forget previous execution of cleaned tasks, use option
*--forget*. This can be made the default behavior by adding the corresponding ``cleanforget``
configuration switch:

.. code-block:: python

    DOIT_CONFIG = {
        'cleanforget': True,
    }

dry run
^^^^^^^

If you want check which tasks the clean operation would affect you can use the option `-n/--dry-run`.

When using a custom action on `dry-run`, the action is not executed at all
**if** it does not include a `dryrun` parameter.

If it includes a `dryrun` parameter the action will **always** be executed,
and its implementation is responsible for handling the *dry-run* logic.

.. literalinclude:: samples/custom_clean.py




ignore
-------

It is possible to set a task to be ignored/skipped (that is, not executed). This
is useful, for example, when you are performing checks in several files and you
want to skip the check in some of them temporarily.

.. literalinclude:: samples/subtasks.py


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

Note the ``!!``, it means that task was ignored. To reverse the `ignore` use
`forget` sub-command.



.. _cmd-status:

status (task graph)
-------------------

*status* shows the task dependency graph as a tree, with the
up-to-date status of every task. It never executes tasks and never saves
any state, so it is safe to run while a pipeline is being developed.

.. code-block:: console

   $ doit status
   ● fetch
   └── ~ build
       ├── ~ publish
       └── ~ report

Roots are tasks without dependencies. The children of a task are the tasks
that depend on it. A task that appears below several parents is expanded once;
other occurrences are shown as ``task ↑``.

==  ===============================================================
 ✓  up-to-date
 ●  will run
 ~  up-to-date itself, but an input file is produced by a task that will run
 !  error, for example an input file that no task produces
 -  ignored
 ?  unknown: task is created at run time (``create_after``)
==  ===============================================================

Options must be given before ``TASK``:

* ``TASK ...``: show the parents (tasks it depends on) and the children (tasks
  that depend on it) of each ``TASK``, with the status and reasons of ``TASK``.
  This is the screen of the interactive navigator (*-i*), printed once: same
  layout code, the columns use a third of the terminal width.
  ``--stale-only``, ``--depth`` and ``--reasons`` do not apply.
* ``--stale-only``: hide up-to-date and ignored tasks.
* ``--depth N``: limit the tree to N levels. Cut-off tasks end with ``…``.
* ``--reasons``: print why each task is not up-to-date.
* *-p*/*--private*: also show tasks that start with an underscore.
* *--all*: show sub-tasks as separate tasks. By default a group task shows the
  worst status of its sub-tasks.
* *-i*/*--interactive*: browse the graph in a full-screen navigator (see
  below). Starts at ``TASK``, or with all tasks listed in the focus column
  when no ``TASK`` is given. Same layout as the static output with ``TASK``.

Interactive mode
^^^^^^^^^^^^^^^^

The graph is laid out left to right: the parents of the focus task on the left,
the focus task in the middle, its children on the right. The cursor
can be on any of them and starts on the focus task. A footer shows the status
and the reasons of the task under the cursor. The navigator starts at ``TASK``.
Without ``TASK`` the middle column lists all tasks (parents and children are
empty); pick one with ↑ ↓ and Enter to make it the focus.

=========  ==========================================
 ←  →      move the cursor one column left / right
 ↑  ↓      move the cursor inside the column
 Enter     make the task under the cursor the focus (cursor returns to it)
 r         show / hide reasons
 R         reload the statuses
 q         quit
=========  ==========================================

Statuses are computed once and the dependency DB file is closed (without saving)
while you navigate, so a ``doit run`` in another terminal is not blocked. ``R``
reads the DB again. Interactive mode needs a terminal for input and output. It draws
with ANSI escape sequences (Windows 10 or later); no extra package is needed.

Like ``doit list --status`` and ``doit info``, *status* evaluates ``uptodate``
entries of tasks (callables run, strings run as shell commands). File
dependencies computed by a ``calc_dep`` task are not part of the graph. Output
uses color when writing to a terminal (disabled by ``NO_COLOR``), and ASCII
symbols when the terminal encoding can not show the default ones.



.. _cmd-auto:

auto (watch)
-------------

.. note::

   Supported on Linux and Mac only.

`auto` is provided through the package `doit-auto1 <https://github.com/pydoit/doit-auto1>`_ plugin.
To install it::

   $ pip install doit-auto1

`auto` sub-command is an alternative way of executing your tasks.  It is a long
running process that only terminates when it is interrupted `Ctrl-C`.
When started it will execute the given tasks. After that it will watch the
file system for modifications in the file-dependencies.
When a file is modified the tasks are re-executed.

.. code-block:: console

    $ doit auto


.. note::

   The `dodo` file is actually re-loaded/executed in a separate process
   every time tasks need to be re-executed.


callbacks
^^^^^^^^^

It is possible to specify shell commands to executed after every cycle
of task execution.
This can used to display desktop notifications, so you do not need to keep
an eye in the terminal to notice when tasks succeed or failed.

Example of sound and desktop notification on Ubuntu.

Contents of a `pyproject.toml` file:

.. code-block:: toml

  [tool.doit.commands.auto]
  success_callback = """
      notify-send -u low -i /usr/share/icons/gnome/16x16/emotes/face-smile.png "doit:   success"; aplay -q /usr/share/sounds/purple/send.wav
      """
  failure_callback = """
      notify-send -u normal -i /usr/share/icons/gnome/16x16/status/error.png "doit:  fail"; aplay -q /usr/share/sounds/purple/alert.wav
      """


Contents of a `doit.cfg` file:

.. code-block:: ini

  [auto]
  success_callback = notify-send -u low -i /usr/share/icons/gnome/16x16/emotes/face-smile.png "doit:   success"; aplay -q /usr/share/sounds/purple/send.wav
  failure_callback = notify-send -u normal -i /usr/share/icons/gnome/16x16/status/error.png "doit:  fail"; aplay -q /usr/share/sounds/purple/alert.wav



``watch`` parameter
^^^^^^^^^^^^^^^^^^^^^

Apart from ``file_dep`` you can use the parameter ``watch`` to pass extra
paths to be watched for (including folders).
If paths are folders their sub-folders will not be watched unless these
sub-folders are also part of the given extra paths.
The ``watch`` parameter can also be specified for a group of "sub-tasks".

.. literalinclude:: samples/empty_subtasks.py


.. _tabcompletion:

tabcompletion
----------------

This command creates a completion for bash or zsh.
The generated script is written on stdout.

bash
^^^^^^

To use a completion script you need to `source` it first.

.. code-block:: console

  $ doit tabcompletion > bash_completion_doit
  $ source bash_completion_doit


zsh
^^^^^

zsh completion scripts should be placed in a folder in the "autoload" path.

.. code-block:: sh

    # add folder with completion scripts
    fpath=(~/.zsh/tabcompletion $fpath)

    # Use modern completion system
    autoload -Uz compinit
    compinit


.. code-block:: console

  $ doit tabcompletion --shell zsh > _doit
  $ cp _doit ~/.zsh/tabcompletion/_doit


hard-coding tasks
^^^^^^^^^^^^^^^^^^^^

If you are creating an application based on `doit`
or if you tasks take a long time to load you may create
a completion script that includes the list of tasks
from your dodo.py.

.. code-block:: console

  $ my_app tabcompletion --hardcode-tasks > _my_app



dumpdb
--------

`doit` saves internal data in a file (`.doit.db` by default).
It uses a binary format (whatever python's dbm is using in your system).
This command will simply dump its content in readable text format in the output.

.. code-block:: console

    $ doit dumpdb



strace
--------

This command uses `strace <https://en.wikipedia.org/wiki/Strace>`_
utility to help you verify which files are being used by a given task.

The output is a list of files prefixed with `R` for open in read mode
or `W` for open in write mode.
The files are listed in chronological order.

This is a debugging feature with many limitations.
  * can strace only one task at a time
  * can only strace CmdAction
  * the process being traced itself might have some kind of cache,
    that means it might not write a target file if it exist
  * does not handle chdir

So this is NOT 100% reliable, use with care!

.. code-block:: console

    $ doit strace <task-name>



reset-dep
---------

This command allows to recompute the information on file dependencies
(timestamp, md5sum, ... depending on the ``check_file_uptodate`` setting), and
save this in the database, without executing the actions.

The command run on all tasks by default, but it is possible to specify a list
of tasks to work on.

This is useful when the targets of your tasks already exist, and you want doit
to consider your tasks as up-to-date. One use-case for this command is when you
change the ``check_file_uptodate`` setting, which cause doit to consider all
your tasks as not up-to-date. It is also useful if you start using doit while
some of your data as already been computed, or when you add a file dependency
to a task that has already run.

.. code-block:: console

    $ doit reset-dep

.. warning::

   `reset-dep` will **NOT** recalculate task `values` and `result`.
   This might not be the correct behavior for your tasks!

   It is safe to use `reset-dep` if your tasks rely only on files to control its
   up-to-date status. So only use this command if you are sure it is OK for your
   tasks.

   If the DB already has any saved `values` or `result` they will be preserved
   otherwise they will not be set at all.
