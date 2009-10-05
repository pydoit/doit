========
Tasks
========

Every *task* must define **actions**. It can optionally defines other attributes like `targets`, `dependencies`, `doc` ...

actions
-----------

Actions define what the task actually do. A task can define any number of actions. There 2 kinds of `actions`: *cmd-action* and *python-action*.

cmd-action
^^^^^^^^^^^

If `action` is a string it will be executed by the shell.

The result of the task follows the shell convention. If the process exits with the value `0` it is successful.  Any other value means the task failed.

python-action
^^^^^^^^^^^^^^

If `action` is a tuple `(callable, *args, **kwargs)` - only `callable` is required. ``args`` is a sequence and  ``kwargs`` is a dictionary that will be used as positional and keywords arguments for the callable. see `*args <http://docs.python.org/tut/node6.html#SECTION006730000000000000000>`_ and `**kwargs <http://docs.python.org/tut/node6.html#SECTION006720000000000000000>`_.

The result of the task is given by the returned value of the ``action`` function. So it must return a *boolean* value `True` to indicate successful completion of the task. Or `False` to indicate task failed. If it raises an exception, it will be considered an error.

example - dynamic
^^^^^^^^^^^^^^^^^^^

It is easy to include dynamic (on-the-fly) behavior to your tasks. Let's take a look at another example:

.. literalinclude:: tutorial/tutorial_02.py


sub-tasks
---------

Most of the time we want to apply the same task several times in different contexts.

The task function can return a python-generator that yields dictionaries. Since each sub-task must be uniquely identified it requires an additional field ``name``.

.. literalinclude:: tutorial/subtasks.py


.. code-block:: console

    eduardo@eduardo:~$ doit
    create_file:file0.txt => Cmd: touch file0.txt
    create_file:file1.txt => Cmd: touch file1.txt
    create_file:file2.txt => Cmd: touch file2.txt
    create_file => Group: create_file:file0.txt, create_file:file1.txt, create_file:file2.txt



groups
------

You can define group of tasks by adding tasks as dependencies and setting its `actions` to ``None``.

.. literalinclude:: tutorial/group.py

Note that task is never executed twice in the same "run".



