More on Task creation
=====================


importing tasks
---------------

The *doit* loader will look at **all** objects in the namespace of the *dodo*.
It will look for functions staring with ``task_`` and objects with
``create_doit_tasks``.
So it is also possible to load task definitions from other
modules just by importing them into your *dodo* file.

.. literalinclude:: tutorial/import_tasks.py

.. code-block:: console

    $ doit list
    echo
    hello
    sample


.. note::

   Importing tasks from different modules is useful if you want to split
   your task definitions in different modules.

   The best way to create re-usable tasks that can be used in several projects
   is to call functions that return task dict's.
   For example take a look at a reusable *pyflakes*
   `task generator <https://github.com/pydoit/doit-py/blob/master/doitpy/pyflakes.py>`_.
   Check the project `doit-py <https://github.com/pydoit/doit-py>`_
   for more examples.



delayed task creation
---------------------


`doit` execution model is divided in two phases:

  - *task-loading* : search for task-creator functions (that starts with string `task_`) and create task metadata

  - *task-execution* : check which tasks are out-of-date and execute them

Normally *task-loading* is completed before the *task-execution* starts.
`doit` allows some task metadata to be modified during *task-execution* with
`calc_deps` and on `uptodate`, but those are restricted to modifying
already created tasks...

Sometimes it is not possible to know all tasks that should be created before
some tasks are executed. For these cases `doit` supports
*delayed task creation*, that means *task-execution* starts before
*task-loading* is completed.

When *task-creator* function is decorated with `doit.create_after`,
its evaluation to create the tasks will be delayed to happen after the
execution of the specified task in the `executed` param.

.. literalinclude:: tutorial/delayed.py


.. note::

   Since the metadata of a delayed task is only created on demand,
   it is currently not possible to set a `basename` for delayed tasks.
   That is because *doit* needs to know which task-creator function should be
   executed in order to create the requested task. See this
   `issue <https://github.com/pydoit/doit/issues/30>`_ for a proposed solution.

.. warning::

   There is a limitation in the use of the delayed task creation with
   multiprocessing. Multiprocessing relies on a task being pickled and
   sent to sub-process, so your task can not contain closures because
   closures are not picklable. See `What can be pickled <https://docs.python.org/3/library/pickle.html#pickle-picklable>`_

   `doit` manages to avoid this limitation for tasks that are created before
   the *task-execution* begins but for delayed tasks it is not possible.


.. _create-doit-tasks:

custom task definition
------------------------

Apart from collect functions that start with the name `task_`.
The *doit* loader will also execute the ``create_doit_tasks``
callable from any object that contains this attribute.


.. literalinclude:: tutorial/custom_task_def.py

The `project letsdoit <https://bitbucket.org/takluyver/letsdoit>`_
has some real-world implementations.

For simple examples to help you create your own check this
`blog post <http://blog.schettino72.net/posts/doit-task-creation.html>`_.


