=====================
More on dependencies
=====================

.. _attr-uptodate:

uptodate
----------

Apart from file dependencies you can extend `doit` to support other ways
to determine if a task is up-to-date through the attribute ``uptodate``.

This can be used in cases where you need to some kind of calculation to
determine if the task is up-to-date or not.

``uptodate`` is a list where each element can be True, False, None, a callable
or a command(string).

 * ``False`` indicates that the task is NOT up-to-date
 * ``True`` indicates that the task is up-to-date
 * ``None`` values will just be ignored. This is used when the value is dynamically calculated


.. note::

  An ``uptodate`` value equal to ``True`` does not override others
  up-to-date checks. It is one more way to check if task is **not** up-to-date.

  i.e. if uptodate==True but a file_dep changes the task is still
  considered **not** up-to-date.


If an ``uptodate`` item is a string it will be executed on the shell.
If the process exits with the code ``0``, it is considered as up-to-date.
All other values would be considered as not up-to-date.

``uptodate`` elements can also be a callable that will be executed on runtime
(not when the task is being created).
The section ``custom-uptodate`` will explain in details how to extend `doit`
writing your own callables for ``uptodate``. This callables will typically
compare a value on the present time with a value calculated on the last
successful execution.

.. note::

  There is no guarantee ``uptodate`` callables or commands will be executed.
  `doit` short-circuit the checks, if it is already determined that the
  task is no `up-to-date` it will not execute remaining ``uptodate`` checks.


`doit` includes several implementations to be used as ``uptodate``.
They are all included in module `doit.tools` and will be discussed in detail
:ref:`later <uptodate_api>`:

  * :ref:`result_dep <result_dep>`: check if the result of another task
    has changed
  * :ref:`run_once <run_once>`: execute a task only once
    (used for tasks without dependencies)
  * :ref:`timeout <timeout>`: indicate that a task should "expire" after
    a certain time interval
  * :ref:`config_changed <config_changed>`: check for changes in
    a "configuration" string or dictionary
  * :ref:`check_timestamp_unchanged`: check access,
    status change/create or modify timestamp of a given file/directory


.. _up-to-date-def:

doit up-to-date definition
-----------------------------

A task is **not** up-to-date if any of:

  * an :ref:`uptodate <attr-uptodate>` item is (or evaluates to) `False`
  * a file is added to or removed from `file_dep`
  * a `file_dep` changed since last successful execution
  * a `target` path does not exist
  * a task has no `file_dep` and `uptodate` item equal to `True`

It means that if a task does not explicitly define any *input* (dependency)
it will never be considered `up-to-date`.

Note that since a `target` represents an *output* of the task,
a missing `target` is enough to determine that a task is not `up-to-date`.
But its existence by itself is not enough to mark a task `up-to-date`.

In some situations, it is useful to define a task with targets but no
dependencies. If you want to re-execute this task only when targets are missing
you must explicitly add a dependency: you could add a ``uptodate`` with ``True``
value or use :ref:`run_once() <run_once>` to force at least one
execution managed by `doit`. Example:

.. literalinclude:: samples/touch.py



Apart from ``file_dep`` and  ``uptodate`` used to determine if a task
is `up-to-date` or not,
``doit`` also includes other kind of dependencies (introduced below)
to help you combine tasks
so they are executed in appropriate order.



.. _uptodate_api:

uptodate API
--------------

This section will explain how to extend ``doit`` writing an ``uptodate``
implementation. So unless you need to write an ``uptodate`` implementation
you can skip this.

Let's start with trivial example. `uptodate` is a function that returns
a boolean value.

.. literalinclude:: samples/uptodate_callable.py

You could also execute this function in the task-creator and pass the value
to to `uptodate`. The advantage of just passing the callable is that this
check will not be executed at all if the task was not selected to be executed.


Example: run-once implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Most of the time an `uptodate` implementation will compare the current value
of something with the value it had last time the task was executed.

We already saw how tasks can save values by returning dict on its actions.
But usually the "value" we want to check is independent from the task actions.
So the first step is to add a callable to the task so it can save some extra
values. These values are not used by the task itself, they are only used
for dependency checking.

The Task has a property called ``value_savers`` that contains a list of
callables. These callables should return a dict that will be saved together
with other task values. The ``value_savers`` will be executed after all actions.

The second step is to actually compare the saved value with its "current" value.

The `uptodate` callable can take two positional parameters ``task`` and ``values``. The callable can also be represented by a tuple (callable, args, kwargs).


   -  ``task`` parameter will give you access to task object. So you have access
      to its metadata and opportunity to modify the task itself!
   -  ``values`` is a dictionary with the computed values saved in the last
       successful execution of the task.


Let's take a look in the ``run_once`` implementation.

.. literalinclude:: samples/run_once.py

The function ``save_executed`` returns a dict. In this case it is not checking
for any value because it just checks it the task was ever executed.

The next line we use the ``task`` parameter adding
``save_executed`` to ``task.value_savers``.So whenever this task is executed this
task value 'run-once' will be saved.

Finally the return value should be a boolean to indicate if the task is
up-to-date or not. Remember that the 'values' parameter contains the dict with
the values saved from last successful execution of the task.
So it just checks if this task was executed before by looking for the
``run-once`` entry in ```values``.


Example: timeout implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's look another example, the ``timeout``. The main difference is that
we actually pass the parameter ``timeout_limit``. Here we present
a simplified version that only accepts integers (seconds) as a parameter.


.. code-block:: python

    class timeout(object):
        def __init__(self, timeout_limit):
            self.limit_sec = timeout_limit

        def __call__(self, task, values):
            def save_now():
                return {'success-time': time_module.time()}
            task.value_savers.append(save_now)
            last_success = values.get('success-time', None)
            if last_success is None:
                return False
            return (time_module.time() - last_success) < self.limit_sec

This is a class-based implementation where the objects are made callable
by implementing a ``__call__`` method.

On ``__init__`` we just save the ``timeout_limit`` as an attribute.

The ``__call__`` is very similar with the ``run-once`` implementation.
First it defines a function (``save_now``) that is registered
into ``task.value_savers``. Than it compares the current time
with the time that was saved on last successful execution.


Example: result_dep implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``result_dep`` is more complicated due to two factors. It needs to modify
the task's ``task_dep``.
And it needs to check the task's saved values and metadata
from a task different from where it is being applied.

A ``result_dep`` implies that its dependency is also a ``task_dep``.
We have seen that the callable takes a `task` parameter that we used
to modify the task object. The problem is that modifying ``task_dep``
when the callable gets called would be "too late" according to the
way `doit` works. When an object is passed ``uptodate`` and this
object's class has a method named ``configure_task`` it will be called
during the task creation.

The base class ``dependency.UptodateCalculator`` gives access to
an attribute named ``tasks_dict`` containing a dictionary with
all task objects where the ``key`` is the task name (this is used to get all
sub-tasks from a task-group). And also a method called ``get_val`` to access
the saved values and results from any task.

See the `result_dep` `source <https://github.com/pydoit/doit/blob/master/doit/task.py>`_.


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

.. literalinclude:: samples/tar.py

.. code-block:: console

    $ doit
    .  version
    .  tar



groups
^^^^^^^

You can define a group of tasks by adding tasks as dependencies and setting
its `actions` to ``None``.

.. literalinclude:: samples/group.py

Note that tasks are never executed twice in the same "run".


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

.. literalinclude:: samples/tsetup.py


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

A cmd-action can also save it's output.
But for this you will need to explicitly import `CmdAction` and set its `save_out`
parameter with the *name* used to save the output in *values*

.. literalinclude:: samples/save_out.py


These values can be used on uptodate_ and getargs_.
Check those sections for examples.


.. _getargs:

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

.. literalinclude:: samples/getargs.py


The values are being passed on to a python-action you can pass the whole dict
by specifying the value name as ``None``.

.. literalinclude:: samples/getargs_dict.py


If a group-task is used, the values from all its sub-tasks are passed as a dict.

.. literalinclude:: samples/getargs_group.py


.. note::
   ``getargs`` creates an implicit setup-task.


.. _attr-calc_dep:

calculated-dependencies
------------------------

Calculation of dependencies might be an expensive operation, so not suitable
to be done on load time by task-creators.
For this situation it is better to delegate
the calculation of dependencies to another task.
The task calculating dependencies must have a python-action returning a
dictionary with `file_dep`, `task_dep`, `uptodate` or another `calc_dep`.

.. note::
   An alternative way (and often easier) to have task attributes that
   rely on other tasks execution is to use `delayed tasks <delayed-task-creation>`.


On the example below ``mod_deps`` prints on the screen all direct dependencies
from a module. The dependencies itself are calculated on task ``get_dep``
(note: get_dep has a fake implementation where the results are taken from a dict).


.. literalinclude:: samples/calc_dep.py



