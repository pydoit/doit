======
Tools
======

Following the *batteries-included* philosophy *doit* includes some common used actions. (well not many by now :p)


run-once (uptodate)
---------------------

see XXX


timeout (uptodate)
---------------------

XXX


create_folder (action)
-------------------------

Creates a folder if it does not exist yet.

.. literalinclude:: tutorial/folder.py


title_with_actions (title)
----------------------------

Return task name task actions from a task. This function can be used as 'title' attribute of a task dictionary to provide more detailed information of the action being executed.

.. literalinclude:: tutorial/titlewithactions.py


set_trace
-----------

`doit` by default redirects stdout and stderr. Because of this when you try to use the python debugger with ``pdb.set_trace``, it does not work propoerly. To make sure you get a propper PDB shell you should use doit.tools.set_trace instead of ``pdb.set_trace``.

.. literalinclude:: tutorial/settrace.py

.. note::

  Note that the orignal stdout is not restored, so the behavior of the program from the point the breakpoint is set might be different.
