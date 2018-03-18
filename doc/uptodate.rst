================
custom uptodate
================

The basics of `uptodate` was already :ref:`introduced <attr-uptodate>`.
Here we look in more
detail into some implementations shipped with `doit`.


.. _result_dep:

result-dependency
----------------------

In some cases you can not determine if a task is "up-to-date" only based on
input files, the input could come from a database or an external process.
*doit* defines a "result-dependency" to deal with these cases without need to
create an intermediate file with the results of the process.

i.e. Suppose you want to send an email every time you run *doit* on a mercurial
repository that contains a new revision number.

.. literalinclude:: samples/taskresult.py


Note the `result_dep` with the name of the task ('version'). `doit` will keep
track of the output of the task *version* and will execute *send_email* only
when the mercurial repository has a new version since last
time *doit* was executed.

The "result" from the dependent task compared between different runs is given
by its last action.
The content for python-action is the value of the returned string or dict.
For cmd-actions it is the output send to stdout plus stderr.

`result_dep` also supports group-tasks. In this case it will check that the
result of all subtasks did not change. And also the existing sub-tasks are
the same.

.. _run_once:


run_once()
---------------

Sometimes there is no dependency for a task but you do not want to execute it
all the time. With "run_once" the task will not be executed again after the first
successful run. This is mostly used together with targets.

Suppose you need to download something from internet.
There is no dependency, but you do not want to download it many times.


.. literalinclude:: samples/download.py

Note that even with *run_once* the file will be downloaded again in case the target is removed.


.. code-block:: console

    $ doit
    .  get_pylogo
    $ doit
    -- get_pylogo
    $ rm python-logo.gif
    $ doit
    .  get_pylogo


.. _timeout:

timeout()
-----------

``timeout`` is used to expire a task after a certain time interval.

i.e. You want to re-execute a task only if the time elapsed since the last
time it was executed is bigger than 5 minutes.

.. literalinclude:: samples/timeout.py


``timeout`` is function that takes an ``int`` (seconds) or ``timedelta`` as a
parameter. It returns a callable suitable to be used as an ``uptodate`` callable.


.. _config_changed:

config_changed()
-----------------

``config_changed`` is used to check if any "configuration" value for the task has
changed. Config values can be a string or dict.

For dict's the values are converted to string (actually it uses python's `repr()`)
and only a digest/checksum of the dictionaries keys and values are saved.

.. literalinclude:: samples/config_params.py


.. _check_timestamp_unchanged:

check_timestamp_unchanged()
-----------------------------

``check_timestamp_unchanged`` is used to check if specified timestamp of a given
file/dir is unchanged since last run.

The timestamp field to check defaults to ``mtime``, but can be selected by
passing ``time`` parameter which can be one of: ``atime``, ``ctime``, ``mtime``
(or their aliases ``access``, ``status``, ``modify``).

Note that ``ctime`` or ``status`` is platform dependent.
On Unix it is the time of most recent metadata change,
on Windows it is the time of creation.
See `Python library documentation for os.stat`__ and Linux man page for
stat(2) for details.

__ http://docs.python.org/library/os.html#os.stat

It also accepts an ``cmp_op`` parameter which defaults to ``operator.eq`` (==).
To use it pass a callable which takes two parameters (prev_time, current_time)
and returns True if task should be considered up-to-date, False otherwise.
Here ``prev_time`` is the time from the last successful run and ``current_time``
is the time obtained in current run.

If the specified file does not exist, an exception will be raised.
If a file is a target of another task you should probably add
``task_dep`` on that task to ensure the file is created before it is checked.

.. literalinclude:: samples/check_timestamp_unchanged.py
