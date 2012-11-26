=========================
Extending `doit`
=========================

`doit` is built to be extended and this can be done in several levels.
So far we have seen:

1) Task creator functions can be placed in a "lib" and them imported in a dodo.py
2) User's can create new ways to define when a task is up-to-date using
   the `uptodate` task parameter
3) The output can be configured by creating custom reports

Apart from those `doit` also expose it's internal API so you can create
new applications on top of `doit`.


task loader customization
===========================

The task loader controls the source/creation of tasks.
Normally `doit` tasks are defined in a `dodo.py` file.
This file is loaded, and the list of tasks is created from
the dict containing task meta-data from the *task-creator* functions.

Subclass TaskLoader to create a custom loader:

.. autoclass:: doit.cmd_base.TaskLoader
   :members: load_tasks


The main program is implemented in the `DoitMain`. It's constructor
takes the an instance of the task loader to be used.

Example: pre-defined task
----------------------------

In the full example bellow a application is created where the only
task available is defined using a dict (so no `dodo.py` will be used).

.. literalinclude:: tutorial/custom_loader.py


Example: load tasks from a module
-------------------------------------

The `ModuleTaskLoader` can be used to load tasks from a specified module,
where this module specifies tasks in the same as specified in `dodo.py`.
`ModuleTaskLoader` is included in `doit` source.

.. literalinclude:: tutorial/module_loader.py



sub-command customization
==============================

The `doit` command line has several sub-commands: `run`, `help`, `list`, `clean`...
By Subclassing `DoitMain.get_commands` it is possible to add/remove commands.

To create a new sub-cmd, subclass `doit.cmd_base.Command`
set some class variables and implement the `execute` method.


.. autoclass:: doit.cmd_base.Command
   :members: execute


Example: scaffolding
----------------------

A common example is applications that provide some kind of scaffolding when
creating new projects.

.. literalinclude:: tutorial/custom_cmd.py

