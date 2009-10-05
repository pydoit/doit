======================
Dependencies & Targets
======================

`dependencies` and `targets` are optional attributes of a task.

Dependency
  A *dependency* indicates an input to the task execution.

Target
  A *target* is the result/output produced by the task execution.

i.e. In a compilation task the source file is a *dependency*, the object file is a *target*.


.. literalinclude:: tutorial/compile.py


up-to-date
----------

`doit` automatically keeps track of file-dependencies. It saves the signature (MD5) of the dependencies every time the task is completed successfully. In case there is no modification in the dependencies and the targets already exist, it skip the task execution to save time, as it would produce the same output from the previous run.

So if there are no modifications to the dependencies and you run `doit` again. The execution of the task's actions is skipped.


.. code-block:: console

  eduardo@eduardo:~$ doit
  compile => Cmd: cc -c main.c
  eduardo@eduardo:~$ doit
  --- compile => Cmd: cc -c main.c

Note the ``---`` (3 dashes) on the command output on the second time it is executed. It means, this task was up-to-date and not executed.



example - lint
--------------

Different from most build-tools dependencies are on tasks not on targets. So `doit` can take advantage of the execute only if not up-to-date feature even for tasks that not define targets.

Lets say you work with a dynamic language (python in this example). You don't need to compile anything but you probably wants to apply a lint-like tool (`PyChecker <http://pychecker.sourceforge.net/>`_) to your source code files. You can define the source code as a dependency to the task.

.. literalinclude:: tutorial/checker.py

.. code-block:: console

   eduardo@eduardo:~$ doit
   checker => Cmd: pychecker sample.py
   eduardo@eduardo:~$ doit
   --- checker => Cmd: pychecker sample.py

Note the ``---`` again.



task-dependency
---------------

We have seen only dependencies on files up to now. On `doit` you can also define **task-dependency**. To define a dependency on another task use the task name (whatever comes after ``task_`` on the function name) preceded by ":". It is used to enforce tasks are executed on the desired order. By default tasks are executed on the same order as they were defined in the `dodo` file.


This example we make sure we include a file with the latest revision number of the bazaar repository on the tar file.

.. literalinclude:: tutorial/tar.py

.. code-block:: console

    eduardo@eduardo:~$ doit
    version => Cmd: bzr version-info > revision.txt
    tar => Cmd: tar -cf foo.tar *



targets
-------

Targets can be any file path (a file or folder). If a target doesn't exist the task will be executed. There is no limitation on the number of targets a task may define.

Lets take the compilation example again.

.. literalinclude:: tutorial/compile.py

If there are no changes in the dependency the task execution is skipped. But if the target is removed the task is also executed again. But only if does not exist. If the target is modified but the dependencies do not change the task is not executed again.

.. code-block:: console

    eduardo@eduardo:~$ doit
    compile => Cmd: cc -c main.c
    eduardo@eduardo:~$ doit
    --- compile => Cmd: cc -c main.c
    eduardo@eduardo:~$ rm main.o
    eduardo@eduardo:~$ doit
    compile => Cmd: cc -c main.c
    eduardo@eduardo:~$ echo xxx > main.o
    eduardo@eduardo:~$ doit
    --- compile => Cmd: cc -c main.c


run-once
--------

Sometimes there is no dependency for a task but you do not want to execute it all the time. If you use ``True`` as dependency the task will not be executed again after the first successful run. This is mostly used together with targets.

Suppose you need to download something from internet. There is no dependency though you do not want to download it many times.

.. literalinclude:: tutorial/download.py

Note that even with *run-once* the file will be downloaded again in case the target is removed.

.. code-block:: console

    eduardo@eduardo:~$ doit
    get_pylogo => Cmd: wget http://python.org/images/python-logo.gif
    eduardo@eduardo:~$ doit
    --- get_pylogo => Cmd: wget http://python.org/images/python-logo.gif
    eduardo@eduardo:~$ rm doc/tutorial/python-logo.gif
    eduardo@eduardo:~$ doit
    get_pylogo => Cmd: wget http://python.org/images/python-logo.gif

.. note::

  Only *file-dependency* and *run-once* are used to determine if a task is up-to-date or not. If a task defines only *task-dependency* or no dependencies at all it will always be executed.

keywords on actions
--------------------

It is common situation to use task information such as *targets*, *dependencies*, or *changed* in its own actions. Note: Dependencies are only *file-dependencies*.

For *cmd-action* you can use the notations of python keyword substitution on strings. The string will contain all values separated by a space (" ").

For *python-action* create a parameter in the function `doit` will take care of passing the value when the function is called. The values are passed as list of strings.

.. literalinclude:: tutorial/hello.py
