=========================
Extending `doit`
=========================

.. _extending:

`doit` is built to be extended and this can be done in several levels.
So far we have seen:

1) User's can create new ways to define when a task is up-to-date using
   the `uptodate` task parameter (:ref:`more <uptodate_api>`)
2) You can customize how tasks are executed by creating new Action types
   (:ref:`more <custom-actions>`)
3) Tasks can be created in different styles by creating custom
   task creators (:ref:`more <create-doit-tasks>`)
4) The output can be configured by creating custom
   reports (:ref:`more <reporter>`)


Apart from those, `doit` also provides a plugin system and
expose it's internal API so you can create new applications on top of `doit`.


.. _custom_loader:

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
takes an instance of the task loader to be used.

Example: pre-defined task
----------------------------

In the full example below a application is created where the only
task available is defined using a dict (so no `dodo.py` will be used).

.. literalinclude:: samples/custom_loader.py


.. _ModuleTaskLoader:

Example: load tasks from a module
-------------------------------------

The `ModuleTaskLoader` can be used to load tasks from a specified module,
where this module specifies tasks in the same way as in `dodo.py`.
`ModuleTaskLoader` is included in `doit` source.

.. literalinclude:: samples/module_loader.py

`ModuleTaskLoader` can take also take a `dict` where its items are functions
or methods of an object.


.. _custom_command:

command customization
=====================

In `doit` a command usually perform some kind of operations on tasks.
`run` to execute tasks, `list` to display available tasks, etc.

Most of the time you should really be creating tasks but
when developing a custom application on top of `doit` it may make sense
to provide some extra commands...

To create a new command, subclass `doit.cmd_base.Command`
set some class variables and implement the `execute` method.


.. autoclass:: doit.cmd_base.Command
   :members: execute


``cmd_options`` uses the same format as
:ref:`task parameters <parameters-attributes>`.


If the command needs to access tasks it should
sub-class `doit.cmd_base.DoitCmdBase`.


Example: scaffolding
----------------------

A common example is applications that provide some kind of scaffolding when
creating new projects.

.. literalinclude:: samples/custom_cmd.py



.. _plugins:

plugins
=======

`doit` plugin system is based on the use of *entry points*, the plugin
does not need to implement any kind of "plugin interface".
It needs only to implement the API of the component it is extending.

Plugins can be enabled in 2 different ways:

- *local plugins* are enabled through the `doit.cfg` file.
- plugins installed with *setuptools* (that provide an entry point),
  are automatically enabled on installation.

Check this `sample plugin <https://github.com/pydoit/doit-plugin-sample>`_
for details on how to create a plugin.


config plugin
-------------

To enable a plugin create a section named after the plugin category.
The value is an entry point to the python class/function/object
that implements the plugin. The format is <module-name>:<attribute-name>.

Example of command plugin implemented in the *class* `FooCmd`,
located at the module `my_plugins.py`::

 [COMMAND]
 foo = my_plugins:FooCmd

.. note::

  The python module containing the plugin must be in the *PYTHONPATH*.


category COMMAND
----------------

Creates a new sub-command. Check :ref:`command <custom_command>` section
for details on how to create a new command.


category BACKEND
----------------

Implements the internal `doit` DB storage system.
Check the module `doit/dependency.py` to see the existing implementation / API.


.. _plugin_reporter:

category REPORTER
-----------------

Register a custom reporter as introduced in the
:ref:`custom reporter<custom_reporter>` section.


category LOADER
----------------

Creates a custom task loader. Check :ref:`loader <custom_loader>` section
for details on how to create a new command.

Apart from getting the plugin you also need to indicate which loader will be
used in the `GLOBAL` section of your config file.

.. code-block:: INI

  [GLOBAL]
  loader = my_loader

  [LOADER]
  my_loader = my_plugins:MyLoader

