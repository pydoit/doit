========
Tasks
========

Every *task* must define **actions**. It can optionally defines other attributes like `targets`, `dependencies`, `doc` ...

Actions define what the task actually do. A task can define any number of actions. There 2 kinds of `actions`: *cmd-action* and *python-action*.

cmd-action
^^^^^^^^^^^

If `action` is a string it will be executed by the shell.

The result of the task follows the shell convention. If the process exits with the value `0` it is successful.  Any other value means the task failed.

python-action
^^^^^^^^^^^^^^

If `action` is a tuple `(callable, *args, **kwargs)` - only `callable` is required. ``args`` is a sequence and  ``kwargs`` is a dictionary that will be used as positional and keywords arguments for the callable. see `Keyword Arguments <http://docs.python.org/tutorial/controlflow.html#keyword-arguments>`_.

The result of the task is given by the returned value of the ``action`` function. So it must return a *boolean* value `True`, `None` or a string to indicate successful completion of the task. Use `False` to indicate task failed. If it raises an exception, it will be considered an error. If it returns any other type it will also be considered an error but this behavior might change in future versions.


example - dynamic
^^^^^^^^^^^^^^^^^^^

It is easy to include dynamic (on-the-fly) behavior to your tasks. Let's take a look at another example:

.. literalinclude:: tutorial/tutorial_02.py

.. note::
  the function `task_hello` is a *task generator* not the task itself. The body of the task generator function is always executed when the dodo file is loaded. Even if the task is not going to be executed. So in this example the line `msg = 3 * "hi! "` will always be executed. From now on when it said that a *task* is executed, read the task's actions are executed.


sub-tasks
---------

Most of the time we want to apply the same task several times in different contexts.

The task function can return a python-generator that yields dictionaries. Since each sub-task must be uniquely identified it requires an additional field ``name``.

.. literalinclude:: tutorial/subtasks.py


.. code-block:: console

    eduardo@eduardo:~$ doit
    create_file:file0.txt
    create_file:file1.txt
    create_file:file2.txt


