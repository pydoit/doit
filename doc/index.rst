About
=====

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task. It will keep track of dependencies between "tasks" and execute them only when necessary.

Unlike other build-tools it allows you to define how/when a task should be considered out-of-date (instead of just checking for changes in files). It makes easy to integrate tasks defined by both python code and external programs (shell commands). Plain python is used to define tasks metadata allowing easy creation of task definition dynamically.

`doit`  was designed to be easy to use and “get out of your way”.


`doit` can be used as:

 * a build tool (generic and flexible)
 * home of your management scripts (it helps you organize and combine shell scripts and python scripts)
 * a functional tests runner (combine together different tools)
 * a configuration management system
 * manage computational pipelines

Features:

 * Easy to use, "no-API"
 * Use python to dynamically create tasks on-the-fly
 * Flexible, adapts to many workflows for creation of tasks/rules/recipes
 * Support for multi-process parallel execution
 * Built-in integration of inotify (automatic re-execution) (linux/mac only)
 * Can be distributed as a standalone (single-file) script
 * Runs on Python 2.5 through 3.2


If you are still wondering why someone would want to use this tool, this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_ explains how everything started.



What people are saying about `doit`
=====================================

  Congratulations! Your tool follows the KISS principle very closely. I always wondered why build tools had to be that complicated. - `Elena <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/#comment-514>`_

  Let me start by saying I'm really lovin doit, at first the interface seemed verbose but quickly changed my mind when I started using it and realised the flexibility.  Many thanks for the great software! - `Michael Gliwinski <https://groups.google.com/d/msg/python-doit/7cD2RiBhB9c/FzrAWkVhEgUJ>`_

  I love all the traditional unix power tools, like cron, make, perl, ..., I also like new comprehensive configuration management tools like CFEngine and Puppet.  But I find doit to be so versatile and so productive. - `Charlie Guo <https://groups.google.com/d/msg/python-doit/JXElpPfcmmM/znvBT0OFhMYJ>`_

  I needed a sort of 'make' tool to glue things together and after trying out all kinds, doit ... has actually turned out to be beautiful. Its easy to add and manage tasks, even complex ones-- gluing things together with decorators and 'library' functions I've written to do certain similar things. - `Matthew <https://groups.google.com/d/msg/python-doit/eKI0uu02ZeY/cBU0RRsO0_cJ>`_


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

* Professional support and consulting services available from ``doit`` creator & maitainer (*schettino72* at gmail.com).

* This web site is hosted on http://sourceforge.net.

* `doit-recipes <https://bitbucket.org/schettino72/doit-recipes/wiki/Home>`_ contains a collection of non-trivial examples and a list of projects using `doit`.


Status
======

`doit` is under active development. Version 0.15 released on 2012-01.

`doit` core features are quite stable. So if there is not recent development, it does NOT mean `doit` is not being mantained... Development is done based on real world use cases. If I don't need a feature and nobody never asked for it, it is not implemented ;) It is well designed and have a very small code base so adding new features isn't hard.

If you use `doit` please drop me a line telling me your experience...
