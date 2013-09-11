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

.. literalinclude:: tutorial/folder.py


title_with_actions (title)
----------------------------

Return task name task actions from a task. This function can be used as 'title' attribute of a task dictionary to provide more detailed information of the action being executed.

.. literalinclude:: tutorial/titlewithactions.py


.. _tools.InteractiveAction:

InteractiveAction (action)
-----------------------------

An InteractiveAction is like a CmdAction but with the following differences:

  * the output is never captured
  * it is always successful (return code is not used)
  * "swallow" KeyboardInterrupt

This is useful for executing long running process like a web-server.

.. literalinclude:: tutorial/interactiveaction.py


PythonInteractiveAction (action)
----------------------------------

Similar to InteractiveAction but for PythonAction.


set_trace
-----------

`doit` by default redirects stdout and stderr. Because of this when you try to use the python debugger with ``pdb.set_trace``, it does not work properly. To make sure you get a proper PDB shell you should use doit.tools.set_trace instead of ``pdb.set_trace``.

.. literalinclude:: tutorial/settrace.py
