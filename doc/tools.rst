======
Tools
======

`doit.tools` includes some commonly used code. These are not used by the `doit`
core, you can see it as a "standard library".
The functions/class used with `uptodate` were already introduced in the previous
section.



create_folder (action)
-------------------------

Creates a folder if it does not exist yet. Uses `os.makedirs() <http://docs.python.org/2/library/os#os.makedirs>_`.

.. literalinclude:: samples/folder.py


title_with_actions (title)
----------------------------

Return task name task actions from a task. This function can be used as 'title' attribute of a task dictionary to provide more detailed information of the action being executed.

.. literalinclude:: samples/titlewithactions.py


.. _tools.LongRunning:

LongRunning (action)
-----------------------------

.. autoclass:: doit.tools.LongRunning


This is useful for executing long running process like a web-server.

.. literalinclude:: samples/longrunning.py


Interactive (action)
----------------------------------

.. autoclass:: doit.tools.Interactive



PythonInteractiveAction (action)
----------------------------------

.. autoclass:: doit.tools.PythonInteractiveAction



set_trace
-----------

`doit` by default redirects stdout and stderr. Because of this when you try to
use the python debugger with ``pdb.set_trace``, it does not work properly.
To make sure you get a proper PDB shell you should use doit.tools.set_trace
instead of ``pdb.set_trace``.

.. literalinclude:: samples/settrace.py


.. _tools.IPython:

IPython integration
----------------------

A handy possibility for interactive experimentation is to define tasks from
within *ipython* sessions and use the ``%doit`` `magic function
<http://ipython.org/ipython-doc/dev/interactive/tutorial.html#magic-functions>`_
to discover and execute them.


First you need to register the new magic function into ipython shell.

.. code-block:: pycon

    >>> %load_ext doit.tools


.. Tip::
    To permanently add this magic-function to your IPython include it on your
    `profile <http://ipython.org/ipython-doc/3/config/intro.html?highlight=profile#profiles>`_,
    create a new script inside your startup-profile
    (i.e. :file:`~/.ipython/profile_default/startup/doit_magic.ipy`)
    with the following content::

        from doit import load_ipython_extension
        load_ipython_extension()

Then you can define your `task_creator` functions and invoke them with `%doit`
magic-function, instead of invoking the cmd-line script with a :file:`dodo.py`
file.


Examples:

.. code-block:: pycon

    >>> %doit --help          ## Show help for options and arguments.

    >>> def task_foo():
            return {'actions': ["echo hi IPython"],
                    'verbosity': 2}

    >>> %doit list            ## List any tasks discovered.
    foo

    >>> %doit                 ## Run any tasks.
    .  foo
    hi IPython
