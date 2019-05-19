==========
Singletons
==========

During the lifecycle of a command invocation, some properties of `doit` are stored in singletons,
provided by the ``doit.globals.Globals`` class.

.. autoclass:: doit.globals.Globals
   :members:

dep_manager
-----------

The doit dependency manager holds the persistent state of `doit`. This includes relations of tasks
among each other or results, returned from their latest runs. It bascially consists of all the
information stored in `doit`'s database file.

The ``dep_manager`` attribute is initialized right before tasks are loaded, which means it allows to
be accessed during *all* task evaluation phases, in particular during:

* Task generation, i.e. from the body of any ``task_*`` function. Task execution, i.e. from the code
* executed by one of the task's actions. Task cleanup, i.e. from the the code executed by one of the
* tasks's clean activities.

An example of this is a task, where at generation time the *target* of the task action is not yet
known, because it is determined during execution. Then it would be possible to store that target in
the dependency manager by returning it from the action. A `clean` action is then able to query
`dep_manager`for that result and perform the cleanup action:


.. literalinclude:: samples/global_dep_manager.py
