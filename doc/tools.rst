======
Tools
======

Following the *batteries-included* philosophy *doit* includes some commonly used functions.


run-once (uptodate)
---------------------

see `run-once`__

__ dependencies.html#run-once


timeout (uptodate)
---------------------

``timeout`` is used to expire a task after a certain time interval.

i.e. You want to re-execute a task only if the time elapsed since the last the time it was executed is bigger than 5 minutes.

.. literalinclude:: tutorial/timeout.py


``timeout`` is function that takes an ``int`` (seconds) or ``timedelta`` as a paramter. It returns a callable suitable to be used as an ``uptodate`` callable.


config_changed (uptodate)
---------------------------

``config_changed`` is used to check if any "configuration" value for the task has changed. Config values can be a string or dict.

For dict's the values are converted to string and only a digest/checksum of the dictionaries keys and values are saved.

.. literalinclude:: tutorial/config_params.py


check_timestamp_unchanged (uptodate)
--------------------------------------

``check_timestamp_unchanged`` is used to check if specified timestamp of a given file/dir is unchanged since last run.  The timestamp field to check defaults to mtime, but can be selected by passing ``time`` parameter which can be one of: atime, access, ctime, status, mtime, modify.

Note that ``ctime`` or ``status`` is platform dependent: time of most recent metadata change on Unix, or the time of creation on Windows.  See `Python library documentation for os.stat`__ and Linux man page for stat(2) for details.

__ http://docs.python.org/library/os.html#os.stat

It also accepts an ``op`` parameter which defaults to ``operator.eq`` (==).  To use it pass a callable which takes two parameters (prev_time, current_time) and returns True if task should be considered up-to-date, False otherwise.

If the specified file does not exist, an exception will be raised, which means e.g. if the file is a target of another task you should probably add ``task_dep`` on that task to ensure the file is created before checking it.

.. literalinclude:: tutorial/check_timestamp_unchanged.py


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
