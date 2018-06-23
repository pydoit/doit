
===================
tutorial 1 - basics
===================

This tutorial demonstrates how to use ``doit`` to create simple computational pipeline.

The goal is to create a graph of python module imports in a package.
`graphviz <http://graphviz.org/>`_'s **dot** tool will be used to generate the graph.

As example the `requests <https://github.com/requests/requests>`_ package will be used. The result is the image below:

.. image:: _static/requests.png




setup
=====

required python packages
------------------------

.. code-block:: console

  $ pip install doit pygraphviz import_deps


sample project
--------------

First create a directory that will contain the projects to be analyzed.

.. code-block:: console

   $ mkdir projects

Then clone the ``requests`` project

.. code-block:: console

   $ cd projects
   $ git clone git@github.com:requests/requests.git
   $ cd ..



finding a module's import
=========================

Using ``import_deps`` list all (intra-packages) imports from a module:

For example:

.. code-block:: console

    $ python -m import_deps projects/requests/requests/models.py
    requests._internal_utils
    requests.auth
    requests.compat
    requests.cookies
    requests.exceptions
    requests.hooks
    requests.status_codes
    requests.structures
    requests.utils


The output contains one imported module per line.


doit task
---------

Next step we are going to wrap the above script in a ``doit`` *task*.
In ``doit`` tasks are defined in a plain python module, by default called ``dodo.py``.

For example a trivial task to execute the script above and save its output into a file would be:


.. code-block:: python3
   :caption: dodo.py

    def task_imports():
        return {
            'actions': ['python -m import_deps '
                        'projects/requests/requests/models.py > requests.models.deps'],
        }


In this module you write functions that are **task-creators**,
the role of these functions is not to execute tasks but to return task's metadata.
**task-creators** are any function whose name starts with ``task_``.
A task name is taken from the function name,
in this case the name is ``imports``.

The most important Task metadata is ``actions``, this defines what will be done when a task is executed.

Note that ``actions`` is list where its element is a string with a shell command.


task execution
--------------

``doit`` command line by default will execute all tasks defined in ``dodo.py`` module in the current directory.

.. code-block:: console

   $ doit
   .  imports


The output reports that the ``imports`` task was executed.
You can check that a file ``requests.models.deps`` was created with
a list of modules imported by ``requests.models``.


incremental computation
-----------------------

One of the main purposes in the usage of ``doit`` is to make use
of **up-to-date** checks to decide if tasks *needs* to be executed or not.

In this case as long as the input file is not modified we are certain
that the same output would be generated...

When dealing with files, task's metadata ``file_dep`` and ``targets`` can be used:


.. task_imports, line 11 is clean
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 5-10,12


Note how ``actions`` can make use of variable substitution for
``%(dependencies)s`` and ``%(targets)s``.

Now let's execute it again:

.. code-block:: console

   $ doit
   .  imports

And then, a second time:

.. code-block:: console

   $ doit
   --  imports


Note that the second time there is a ``--`` instead of ``.`` before the task name.
This means that the task was not executed, ``doit`` understood that
the task output would be the same as previously executed,
so it does not execute the task again.

.. warning::

   When ``doit`` *loads* a ``dodo.py`` file it executes all *task-creator* functions in order to generate all tasks metadata.
   A task's ``action`` is only executed if the task is selected to run and not **up-to-date**.

   Expensive computation should always be done on task's ``action``
   and never on the body of a **task-creator** function.


rules for up-to-date checks on files
------------------------------------


file_dep
^^^^^^^^

``doit`` uses the *md5* of ``file_dep`` to determine if a dependency is changed.


.. code-block:: console

   $ touch projects/requests/requests/models.py
   $ doit
   -- imports
   $ echo "# comment" >> projects/requests/requests/models.py
   $ doit
   .  imports


Note that simply changing a file timestamp would not trigger a new execution.


targets
^^^^^^^

For ``targets``, it only checks if the target exists.
So if a target is removed it will be re-created even without changes on dependencies.

.. code-block:: console

   $ rm requests.models.deps
   $ doit
   .  imports



graphviz dot
============


Next step we will create a `graphviz <http://graphviz.org/>`_'s ``dot`` file.
``dot`` is a language to describe to graphs.

Code below defines a python function to read a file containing
import dependencies (as generated by previously defined ``imports`` task).


.. module_to_dot()
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 1-3,14-15,18-27


Task with python action
-----------------------

Next we define the task ``dot``, it is similar to previous task...
but note that instead of passing a string with a shell command
we directly pass the previously created python function ``module_to_dot``.



.. task_dot()
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 28-33,35


Also note the function takes the special parameters ``dependencies`` and ``targets``, those values will be injected by ``doit``.


.. code-block:: console

   $ doit
   -- imports
   .  dot


To indicate a failure, a python-action should return the value ``False`` or raise an exception.



graph image
-----------

Finally lets add another task to generate an image from the `dot` file using the graphviz command line tool.


.. task_draw()
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 38-43,45



.. code-block:: console

   $ doit
   -- imports
   -- dot
   .  draw


Opening the file ``requests.models.png`` you should get the image below:

.. image:: _static/requests.models.png



doit command line
=================


``doit`` has a rich (and extensible) command line to manipulate your tasks. So far we have only executed ``doit`` without any parameters...

``doit`` command line takes the form of ``doit <sub-command> <options> <arguments>``,
where ``options`` and ``arguments`` are specific to the ``sub-command``.

If no sub-command is specified the default command ``run`` is used.
``run`` executes tasks...


doit help
---------

``doit help`` will list all available sub-commands.

You can also get help for a specific sub-command with ``doit help <sub-command>``, i.e. ``doit help run``.


doit list
---------

The command ``list`` displays the list of known tasks:

.. code-block:: console

   $ doit list
   dot       generate a graphviz's dot graph from module imports
   draw      generate image from a dot file
   imports   find imports from a python module


Note how the docstring from task-creators functions were used as task's description.


info
----

The ``info`` command can be used to get more information from a specific task.
Information about it's metadata, and it is state (whether it is up-to-date or not).


.. code-block:: console

   $ doit info imports

   imports

   find imports from a python module

   status     : up-to-date

   file_dep   :
     - projects/requests/requests/models.py

   targets    :
     - requests.models.deps


run
---

``run`` is the default command, and usually not explicitly typed.
So ``$ doit`` and ``$ doit run`` do exactly the same thing.

Without any parameters ``run`` will execute all of your tasks.
You can also select which tasks to be executed by passing a sequence of tasks names.

For example if you want to execute only the ``imports`` task you would type:


.. code-block:: console

   $ doit imports
   -- imports


Note that even if you explicitly pass the name of task to be executed,
``doit`` will actually execute the task only if it is not up-to-date.

You can also pass more than one task:

.. code-block:: console

   $ doit imports dot
   -- imports
   -- dot


Another important point to take notice is that even
if you specify only one task ``doit`` will run all of the dependencies of the specified task.

.. code-block:: console

   $ doit dot
   -- imports
   -- dot


Note how the ``imports`` task was run because task ``dot`` has ``file_dep`` that is a target of ``imports`` task.


clean
-----

A common use-case is to be able to "revert" the operations done by a task.
``doit`` provides the ``clean`` command for that.

By default it does nothing... You need to add a parameter ``clean`` to task metadata. You write custom ``actions`` (shell or python) of what should be done. But for the most common case you just want to remove the created targets. For that you can just pass the value ``True``.


Add ``clean`` to all defined tasks, like:

.. task_draw()
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 38-45
   :emphasize-lines: 7


Executing ``clean``:

.. code-block:: console

   $ doit clean
   draw - removing file 'requests.models.png'
   dot - removing file 'requests.models.dot'
   imports - removing file 'requests.models.deps'


Since targets were removed this will force the tasks to be executed on next ``run``.

.. code-block:: console

   $ doit
   .  imports
   .  dot
   .  draw



forget
------

``doit`` will look for changes in dependencies, but not changes in your code... While developing a task it is common to want to force the execution of task.

For example lets change the colors of nodes in graph:

.. module_to_dot()
.. literalinclude:: tutorial/tuto_1_1.py
   :language: python3
   :lines: 14-21
   :emphasize-lines: 3-4


To force its execution we need to ``doit`` to ``forget`` its state like:

.. code-block:: console

   $ doit forget dot
   forgetting dot

.. code-block:: console

   $ doit
   -- imports
   .  dot
   .  draw


.. image:: _static/requests.models-blue.png


.. note::

   The ``run`` command also has the option ``-a/--always-execute`` that will ignore the **up-to-date** check and always execute tasks.



Pipelines
=========

So far we have relied on the pipeline based on files. Where one task's target is used as a dependency in another task.

While ``doit`` provides first-class support for file based pipelines, they are not required.

get module imports - python
---------------------------

Let's rewrite the ``imports`` task to use python action:

.. task_imports()
.. literalinclude:: tutorial/tuto_1_2.py
   :language: python3
   :lines: 4-19
   :emphasize-lines: 8,15



Function ``get_imports`` is used as task's action.
It returns a dictionary, this will be saved by ``doit`` in its internal database. The returned dictionary must contain only values that can be encoded in JSON.

Note that the parameter ``module_path`` is passed into task definition of ``actions``.
Instead of just specifying a callable it takes a tuple *(callable, args, kwargs)*.



getargs
-------

The task parameter ``getargs`` can be used to specify values that are
computed in another task.
It is a dictionary where the *key* is the parameter name used in this task's action parameter.
It's value is 2-value tuple where the first item is the task name, and the second is the value name (key in the returned dictionary).



.. task_dot()
.. literalinclude:: tutorial/tuto_1_2.py
   :language: python3
   :lines: 22-38
   :emphasize-lines: 1,14,15


Note how ``module_to_dot`` takes 3 parameters:

- ``source``: value is passed directly when task's actions is defined
- ``imports``: value is taken from ``imports`` task result
- ``targets``: values is taken from Task metadata


Everything should work as before, without the creation of intermediate files.

``doit`` can determine if ``imports`` is **up-to-date** even without a target file (it just look at the ``file_dep``).

``doit`` can also determine if ``dot`` is **up-to-date** by comparing the value returned by ``imports`` (instead of checking for file changes, it checks for changes in the JSON object).



package imports
===============

So far we are creating a graph of only one module.
Let's process all modules in the package.

``doit`` has the concept of a **task-group**.
A task group performs the same operation over a set of instances.
To create a task group the task-creator function should ``yield`` one more task dictionaries with task metadata.

Note that each task is still independent.
Since each task needs to be independently identified an extra parameter ``name`` must be provided.


.. task_imports()
.. literalinclude:: tutorial/tuto_1_3.py
   :language: python3
   :lines: 8-22
   :emphasize-lines: 4,11,12


Sub-tasks (items of task group) by default are not reported on ``list`` command. They be displayed using the ``--all`` flag.

.. code-block:: console

   $ doit list
   dot       generate a graphviz's dot graph from module imports
   draw      generate image from a dot file
   imports   find imports from a python module

.. code-block:: console

   $ doit list --all imports
   imports                            find imports from a python module
   imports:requests.__init__
   imports:requests.__version__
   imports:requests._internal_utils
   imports:requests.adapters
   imports:requests.api
   imports:requests.auth
   imports:requests.certs
   imports:requests.compat
   imports:requests.cookies
   imports:requests.exceptions
   imports:requests.help
   imports:requests.hooks
   imports:requests.models
   imports:requests.packages
   imports:requests.sessions
   imports:requests.status_codes
   imports:requests.structures
   imports:requests.utils


Note the task name is composed by the (base name) group task name
followed by a colon `:` and the `name` specified as a parameter.

From command line a single task can executed like::

  $ doit imports:requests.models
  .  imports:requests.models


getargs from group-task
-----------------------

``getargs`` can also be used to get values from a *group-task*.
The difference is that its value will be a dictionary where the
key is the sub-task name:


.. task_dot()
.. literalinclude:: tutorial/tuto_1_3.py
   :language: python3
   :lines: 25-41
   :emphasize-lines: 5,15


Finally adjust task ``draw``.

.. task_draw()
.. literalinclude:: tutorial/tuto_1_3.py
   :language: python3
   :lines: 44-51
   :emphasize-lines: 4-5


Running ``doit`` you should get the file ``requests.png`` with the image below:

.. image:: _static/requests.png


verbosity
=========


TODO


DOIT_CONFIG
===========

TODO
