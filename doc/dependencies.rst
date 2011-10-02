======================
Dependencies & Targets
======================


up-to-date tasks
--------------------

One of the main ideas of `doit` and other build-tools is to check if the tasks/targets are **up-to-date**. In case there is no modification in the dependencies and the targets already exist, it skip the task execution to save time, as it would produce the same output from the previous run.

Dependency
  A dependency indicates an input to the task execution.

Target
  A *target* is the result/output file produced by the task execution.


i.e. In a compilation task the source file is a *file_dep*, the object file is a *target*.

.. literalinclude:: tutorial/compile.py


`doit` automatically keeps track of file dependencies. It saves the signature (MD5) of the dependencies every time the task is completed successfully.

So if there are no modifications to the dependencies and you run `doit` again. The execution of the task's actions is skipped.


.. code-block:: console

  $ doit
  .  compile
  $ doit
  -- compile

Note the ``--`` (2 dashes, one space) on the command output on the second time it is executed. It means, this task was up-to-date and not executed.


file_dep (file dependency)
-----------------------------

Different from most build-tools dependencies are on tasks not on targets. So `doit` can take advantage of the "execute only if not up-to-date" feature even for tasks that not define targets.

Lets say you work with a dynamic language (python in this example). You don't need to compile anything but you probably wants to apply a lint-like tool (`PyChecker <http://pychecker.sourceforge.net/>`_) to your source code files. You can define the source code as a dependency to the task.


.. literalinclude:: tutorial/checker.py

.. code-block:: console

   $ doit
   .  checker
   $ doit
   -- checker

Note the ``--`` again to indicate the execution was skipped.

Traditional build-tools can only handle files as "dependencies". `doit` has several ways to check for dependencies, those will be introduced later.


targets
-------

Targets can be any file path (a file or folder). If a target doesn't exist the task will be executed. There is no limitation on the number of targets a task may define.

Lets take the compilation example again.

.. literalinclude:: tutorial/compile.py

If there are no changes in the dependency the task execution is skipped. But if the target is removed the task is also executed again. But only if does not exist. If the target is modified but the dependencies do not change the task is not executed again.

.. code-block:: console

    $ doit
    .  compile
    $ doit
    -- compile
    $ rm main.o
    $ doit
    .  compile
    $ echo xxx > main.o
    $ doit
    -- compile


execution order
-----------------

If your tasks interact in a way where the target (output) of one task is a file_dep (input) of another task, `doit` will make sure your tasks are executed in the correct order.

.. literalinclude:: tutorial/taskorder.py

.. code-block:: console

  $ doit
  .  create
  .  modify


result-dependency
----------------------

In some cases you can not determine if a task is "up-to-date" only based on some input files, the input could come from a database or an extrernal process. *doit* defines a "result-dependency" to deal with these cases without need to create an intermediate file with the reulsts of the process.

i.e. Suppose you want to send an email everytime you run *doit* on a bazaar repository that contains a new revision number.

.. literalinclude:: tutorial/taskresult.py

Note the `result_dep` with the name of the task (version). `doit` will keep track of the output of the task *version* and will execute *send_email* only when the bazaar repository has a new version since last time *doit* was executed.

The "result" from the dependent task compared between different runs is given by its last action. The content for python-action is the value of the returned string. For cmd-actions is the output send to stdout plus stderr.


saving computed values
------------------------

Tasks can save computed values by returning a dictionary on it's python-actions. The values must be JSON encodable.

These values can be used on uptodate_ and getargs_. Check those sections for examples.


uptodate
----------

`doit` also supports checking if a task is up-to-date directly by the parameter `uptodate`.

This can be used in cases where you need to some kind of calculation to determine if the task is up-to-date or not. i.e. you check if a value in a database is smaller than a certain value.

`uptodate` is a list where each element can be True, False, None or a callable.

 * ``False`` indicates that the task is NOT up-to-date
 * ``True`` indicates that the task is up-to-date
 * ``None`` values will just be ignored. This is used when the value is dinamically calculated

.. note::

  ``uptodate`` value ``True`` does not override others up-to-date checks. It is one more way to check if task is **not** up-to-date.

   i.e. if uptodate==True but a file_dep changes the task is still considered **not** up-to-date.


`uptodate` elements can also be a callable that returns False, True or None. This callable must take at least two positional parameters ``task`` and ``values``. The callable can also be represented by a tuple (callable, args, kwargs).

   -  ``task`` parameter will give you access to task object. So you have access to its metadata and opportunity to modifiy the task itself!
   -  ``values`` is a dictionary with the computed values saved in the last successful execution of the task.

.. literalinclude:: tutorial/uptodate_callable.py


run-once
^^^^^^^^^^

Here is a simple example on how to use the positional parameters of ``uptodate``.

Sometimes there is no dependency for a task but you do not want to execute it all the time. If "run_once" the task will not be executed again after the first successful run. This is mostly used together with targets.

Suppose you need to download something from internet. There is no dependency though you do not want to download it many times.


.. literalinclude:: tutorial/run_once.py

First a new action is added to task, this action will just save a computed value for the task. So whenever this task is executed this task value 'run-once' will be saved. The 'values' parameter contains the dict with the values saved from last successful execution of the task. ``run_once`` will just check if this task was executed looking for the ``run-once`` in ```values``.

Since "run_once" is a common pattern it is included in ``doit.tools`` module.


.. literalinclude:: tutorial/download.py

Note that even with *run_once* the file will be downloaded again in case the target is removed.


.. code-block:: console

    $ doit
    .  get_pylogo
    $ doit
    -- get_pylogo
    $ rm python-logo.gif
    $ doit
    .  get_pylogo


.. note::

  If you want to use other tasks to calculate ``uptodate`` you should combine it with ``calc_deps``.


.. note::

  `doit.tools`__ includes four ``uptodate`` callables that are ready to use. ``run_once`` as described above. ``timeout`` that will make your task up-to-date only during a certain time interval. ``config_changed`` will check for changes in a "configuration" string or dictionary. ``check_timestamp_unchanged`` will check access, status change/create or modify timestamp of a given file/directory.

__ tools.html


doit up-to-date definition
-----------------------------

A task is **not** up-to-date if any of `file_dep`, `result_dep`, or `uptodate` is not up-to-date or there is a missing `target`. If a task does not define any of these dependencies it will always be executed.

Apart from these dependencies used to determine if a task is up-to-date or not. ``doit`` also include other kind of dependencies to help you combine tasks so they are executed in appropriate order.



calculated-dependencies
------------------------

Calculation of dependencies might be an expensive operation, so not suitable to be done on task-generators. For this situation is better to delegate the calculation of dependencies to another task. The task calcutating dependencies must have a python-action returning a dictionary with `file_dep`, `task_dep`, `result_dep`, `uptodate` or another `calc_dep`.

On the example below ``mod_deps`` prints on the screen all direct dependencies from a module. The dependencies itself are calculated on task ``get_dep`` (note: get_dep has a fake implementation where the results are taken from a dict).


.. literalinclude:: tutorial/calc_dep.py



task-dependency
---------------

It is used to enforce tasks are executed on the desired order. By default tasks are executed on the same order as they were defined in the `dodo` file. To define a dependency on another task use the task name (whatever comes after ``task_`` on the function name) in the "task_dep" attribute.


.. note::

  A *task-dependency* **only** indicates that another task should be "executed" before itself. The task-dependency might not really be executed if it is *up-to-date*.

.. note::

  *task-dependency* s are **not** used to determine if a task is up-to-date or not. If a task defines only *task-dependency* it will always be executed.


This example we make sure we include a file with the latest revision number of the bazaar repository on the tar file.

.. literalinclude:: tutorial/tar.py

.. code-block:: console

    $ doit
    .  version
    .  tar


.. note::

  a *task-dependency* is executed before checking if the task is up-to-date. If you want to execute another task only if it is not up-to-date you should use a ``setup`` task.


groups
^^^^^^^

You can define group of tasks by adding tasks as dependencies and setting its `actions` to ``None``.

.. literalinclude:: tutorial/group.py

Note that tasks are never executed twice in the same "run".


setup-task
---------------------

Some tasks require some kind of environment setup. Tasks may have a list of "setup" tasks.

* the setup-task will be executed only if the task is to be executed (not up-to-date)
* setup-tasks are just normal tasks that follow all other task behavior


teardown
^^^^^^^^^^^^^^^^
Task may also define 'teardown' actions. These actions are executed after all tasks have finished their execution. They are executed in reverse order their tasks were executed.


Example:

.. literalinclude:: tutorial/tsetup.py


getargs
--------

`getargs` provides a way to use values computed from one task in another task.

For *cmd-action* use dictionary-based string formatting.

For *python-action* the action callable parameter names must match with keys from `getargs`.

.. literalinclude:: tutorial/getargs.py

.. note::
   ``getargs`` creates an implicit setup-task.



keywords on actions
--------------------

It is common situation to use task information such as *targets*, *dependencies*, or *changed* in its own actions. Note: Dependencies are only *file-dependencies*.

For *cmd-action* you can use the python notation for keyword substitution on strings. The string will contain all values separated by a space (" ").

For *python-action* create a parameter in the function `doit` will take care of passing the value when the function is called. The values are passed as list of strings.

.. literalinclude:: tutorial/hello.py

