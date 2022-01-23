.. meta::
   :description: Accessing doit internal database
   :keywords: python, doit, documentation, guide, database, status

.. title:: Accessing doit internal database  - pydoit guide


==================================
Globals - accessing doit internals
==================================

During the life-cycle of a command invocation,
some properties of `doit` are stored in global singletons,
provided by the ``doit.Globals`` class.

.. autoclass:: doit.globals.Globals
   :members:

dep_manager
-----------

The doit dependency manager holds the persistent state of `doit`.
This includes relations of tasks among each other or results,
returned from their latest runs. It basically consists of all the
information stored in `doit`'s database file.

The ``dep_manager`` attribute is initialized right before tasks are loaded,
which means it allows to be accessed during *all* task evaluation phases,
in particular during:

* Task creation, i.e. from the body of any ``task_*`` function.
* Task execution, i.e. from the code executed by one of the task's actions.
* Task cleanup, i.e. from the the code executed by one of the tasks's clean activities.

The `Dependency` class has members to access persistent doit data via its API:

.. autoclass:: doit.dependency.Dependency
   :members: get_values, get_value, get_result

The class internally interacts with a data base backend
which may be accessed via the `backend` attribute.
An experienced user may also *modify* persistently stored *doit* data through that attribute.
As an example of a backend API,
look at the common methods exposed by the default `DbmDB` backend implementation:

.. class:: doit.dependency.DbmDB

   A simple Key-Value database interface

   .. automethod:: doit.dependency.DbmDB.get
   .. automethod:: doit.dependency.DbmDB.set
   .. automethod:: doit.dependency.DbmDB.remove

There are other backends available in *doit*,
see the documentation on :ref:`db_backends` on how to select between them.


``dep_manager`` example
+++++++++++++++++++++++

An example of using the exposed dependency manager is a task,
where at creation time the *target* of the task action is not yet known,
because it is determined during execution.
Then it would be possible to store that target in the dependency manager
by returning it from the action.
A `clean` action is subsequently able to query `dep_manager` for that result
and perform the cleanup action:


.. literalinclude:: samples/global_dep_manager.py
