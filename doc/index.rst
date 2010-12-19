About
=====

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task. It will keep track of dependencies between "tasks" and execute them only when necessary. It was designed to be easy to use and "get out of your way".

Features:

 * Easy to use, "no-API"
 * Use python to dynamically create tasks on-the-fly
 * Flexible, adapts to many workflows for creation of tasks/rules/recipes
 * Support for multi-process parallel execution
 * Built-in integration of inotify (automatically re-execution) (linux/mac only)

`doit` can be used as:

 * a build tool (generic and flexible)

 * home of your management scripts (it helps you organize and combine shell scripts and python scripts)

 * a functional tests runner (combine together different tools)


If you are still wondering why someone would want to use this tool, check this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_.


Quick Start
============

install::

  $ pip install doit

It looks like... python!

`dodo.py`

.. literalinclude:: tutorial/hello.py

run

.. code-block:: console

  $ doit
  .  hello
  $ cat hello.txt
  Hello World!!!
  Python says Hello World!!!


Go on, read the `documentation <contents.html>`_


Project Details
===============

* This is an open-source project (`MIT license <http://opensource.org/licenses/mit-license.php>`_) written in python.

* Download from `PyPi <http://pypi.python.org/pypi/doit>`_

* Project management (bug tracker, feature requests and source code ) on `launchpad <https://launchpad.net/doit>`_.

* `Documentation <contents.html>`_

* Questions and feedback on `google group <http://groups.google.co.in/group/python-doit>`_.

* This web site is hosted on http://sourceforge.net.



Status
======

`doit` is under active development. Version 0.9 released on 2010-06.

Development is done based on real world use cases. If I don't need a feature and nobody never asked for it, it is not implemented ;) It is well designed and have a very small code base so adding new features isn't hard. `doit` already provides most features I need, so the development of new features has slowed down.

If you use `doit` please drop me a line telling me your experience...
