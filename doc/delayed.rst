======================
delayed task creation
======================


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


.. warning::

   There is a limitation in the use of the delayed task creation with
   multiprocessing. Multiprocessing relies on a task being pickled and
   sent to sub-process, so your task can not contain closures because
   closures are not picklable. See `What can be pickled <https://docs.python.org/3/library/pickle.html#pickle-picklable>`_

   `doit` manages to avoid this limitation for tasks that are created before
   the *task-execution* begins but for delayed tasks it is not possible.

