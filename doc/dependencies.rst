=====================
More on dependencies
=====================

uptodate
----------

Apart from file dependencies you can extend `doit` to support other ways
to determine if a task is up-to-date throught the attribute ``uptodate``.

This can be used in cases where you need to some kind of calculation to
determine if the task is up-to-date or not.

``uptodate`` is a list where each element can be True, False, None or a callable.

 * ``False`` indicates that the task is NOT up-to-date
 * ``True`` indicates that the task is up-to-date
 * ``None`` values will just be ignored. This is used when the value is dinamically calculated


.. note::

  An ``uptodate`` value equal to ``True`` does not override others
  up-to-date checks. It is one more way to check if task is **not** up-to-date.

  i.e. if uptodate==True but a file_dep changes the task is still
  considered **not** up-to-date.


``uptodate`` elements can also be a callable that will be executed on runtime
(not when the task is being created).
The section ``custom-uptodate`` will explain in details how to extend `doit`
writing your own callables for ``uptodate``. This callables will tipically
compare a value on the present time with a value calculated on the last
successful execution.

`doit` includes several implementations to be used as ``uptodate``.
They are all included in module `doit.tools` and will be discussed in detail
later:

  * ``result_dep``: check if the result of another task has changed
  * ``run_once``: execute a task only once (used for tasks wihtout dependencies)
  * ``timeout``: indicate that a task should "expire" after a certain time interval
  * ``config_changed``: check for changes in a "configuration" string or dictionary
  * ``check_timestamp_unchanged``: check access, status change/create or modify timestamp of a given file/directory


doit up-to-date definition
-----------------------------

A task is **not** up-to-date if any of `file_dep` or `uptodate` is not up-to-date
or there is a missing `target`.
If a task does not define any of these dependencies it will always be executed.

Apart from these dependencies used to determine if a task is up-to-date or not.
``doit`` also include other kind of dependencies to help you combine tasks
so they are executed in appropriate order.



task-dependency
---------------

It is used to enforce tasks are executed on the desired order.
By default tasks are executed on the same order as they were defined in
the `dodo` file. To define a dependency on another task use the
task name (whatever comes after ``task_`` on the function name) in the
"task_dep" attribute.


.. note::

  A *task-dependency* **only** indicates that another task should be "executed"
  before itself. The task-dependency might not really be executed if it
  is *up-to-date*.

.. note::

  *task-dependencies* are **not** used to determine if a task is up-to-date or
  not. If a task defines only *task-dependency* it will always be executed.


This example we make sure we include a file with the latest revision number of
the mercurial repository on the tar file.

.. literalinclude:: tutorial/tar.py

.. code-block:: console

    $ doit
    .  version
    .  tar



groups
^^^^^^^

You can define group of tasks by adding tasks as dependencies and setting
its `actions` to ``None``.

.. literalinclude:: tutorial/group.py

Note that tasks are never executed twice in the same "run".


calculated-dependencies
------------------------

Calculation of dependencies might be an expensive operation, so not suitable
to be done on load time by task-creators.
For this situation is better to delegate
the calculation of dependencies to another task.
The task calcutating dependencies must have a python-action returning a
dictionary with `file_dep`, `task_dep`, `uptodate` or another `calc_dep`.

On the example below ``mod_deps`` prints on the screen all direct dependencies
from a module. The dependencies itself are calculated on task ``get_dep``
(note: get_dep has a fake implementation where the results are taken from a dict).


.. literalinclude:: tutorial/calc_dep.py



setup-task
-------------

Some tasks may require some kind of environment setup.
In this case they can define a list of "setup" tasks.

* the setup-task will be executed only if the task is to be executed (not up-to-date)
* setup-tasks are just normal tasks that follow all other task behavior

.. note::

  A *task-dependency* is executed before checking if the task is up-to-date.
  A *setup-task* is executed after the checking if the task is up-to-date and
  it is executed only if the task is not up-to-date and will be executed.


teardown
^^^^^^^^^^^
Task may also define 'teardown' actions.
These actions are executed after all tasks have finished their execution.
They are executed in reverse order their tasks were executed.


Example:

.. literalinclude:: tutorial/tsetup.py


.. code-block:: console

    $ doit withenvX
    .  setup_sample:setupX
    start setupX
    .  withenvX:c
    x c
    .  withenvX:b
    x b
    .  withenvX:a
    x a
    stop setupX
    $ doit withenvY
    .  setup_sample:setupY
    start setupY
    .  withenvY
    y
    stop setupY


saving computed values
------------------------

Tasks can save computed values by returning a dictionary on it's python-actions.
The values must be JSON encodable.

These values can be used on uptodate_ and getargs_.
Check those sections for examples.



getargs
--------

`getargs` provides a way to use values computed from one task in another task.
The values are taken from "saved computed values"
(returned dict from a python-action).

For *cmd-action* use dictionary-based string formatting.

For *python-action* the action callable parameter names must match with keys
from `getargs`.

`getargs` is a dictionary where the key is the argument name used on actions,
and the value is a tuple with 2 strings: task name, "value name".

.. literalinclude:: tutorial/getargs.py


The values are being passed on to a python-action you can pass the whole dict
by specifying the value name as ``None``.

.. literalinclude:: tutorial/getargs_dict.py


If a group-task is used, the values from all its sub-tasks are passed as a list.

.. literalinclude:: tutorial/getargs_group.py


.. note::
   ``getargs`` creates an implicit setup-task.



keywords on actions
--------------------

It is common situation to use task information such as *targets*,
*dependencies*, or *changed* in its own actions.
Note: Dependencies here refers only to *file-dependencies*.

For *cmd-action* you can use the python notation for keyword substitution
on strings. The string will contain all values separated by a space (" ").

For *python-action* create a parameter in the function, `doit` will take care
of passing the value when the function is called.
The values are passed as list of strings.

.. literalinclude:: tutorial/hello.py

