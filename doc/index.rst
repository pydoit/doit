About
=====

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task.


build-tools
------------

Build-tools were created with two primary goals:

1) To keep track of inter-dependencies between tasks and ensure that they will be executed in the correct order.

2) To be faster than manually executing all tasks. Actually it can not really execute a given task faster, instead it has some mechanism to determine if a task is up-to-date or not. So it is faster by executing less tasks, executing only the ones required (not up-to-date).

For more details check the `Software Carpentry's lecture <http://software-carpentry.org/4_0/make/intro/>`_.


why `doit`?
-------------

Task's metadata (actions, dependencies, targets...) are better described in a declarative way, but often you want to create this metadata programmatically.

 * In `doit` plain python is used to define task's metadata allowing easy creation of tasks dynamically.

 * In `doit` it is possible to integrate task's actions defined by both python code and external programs (shell commands).

 * In `doit` tasks dependencies can be calculated at execution time by another task.


Traditional build-tools were created mainly to deal with compile/link process of source code. `doit` was designed to solve a broader range of tasks.

 * Unlike other build-tools `doit` allows you to define how/when a task should be considered up-to-date (instead of just checking for changes in files).


`doit`  was designed to be easy to use and “get out of your way”.


`doit` can be used as
-----------------------

 * a build tool (generic and flexible)
 * home of your management scripts (it helps you organize and combine shell scripts and python scripts)
 * a functional tests runner (combine together different tools)
 * a configuration management system
 * manage computational pipelines

Features
----------

 * Easy to use, "no-API"
 * Use python to dynamically create tasks on-the-fly
 * Flexible, adapts to many workflows for creation of tasks/rules/recipes
 * Support for multi-process parallel execution
 * Built-in integration of inotify (automatic re-execution) (linux/mac only)
 * Can be distributed as a standalone (single-file) script
 * Runs on Python 2.5 through 3.2


This blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_ explains how everything started.



What people are saying about `doit`
=====================================

  Congratulations! Your tool follows the KISS principle very closely. I always wondered why build tools had to be that complicated. - `Elena <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/#comment-514>`_

  Let me start by saying I'm really lovin doit, at first the interface seemed verbose but quickly changed my mind when I started using it and realized the flexibility.  Many thanks for the great software! - `Michael Gliwinski <https://groups.google.com/d/msg/python-doit/7cD2RiBhB9c/FzrAWkVhEgUJ>`_

  I love all the traditional unix power tools, like cron, make, perl, ..., I also like new comprehensive configuration management tools like CFEngine and Puppet.  But I find doit to be so versatile and so productive. - `Charlie Guo <https://groups.google.com/d/msg/python-doit/JXElpPfcmmM/znvBT0OFhMYJ>`_

  I needed a sort of 'make' tool to glue things together and after trying out all kinds, doit ... has actually turned out to be beautiful. Its easy to add and manage tasks, even complex ones-- gluing things together with decorators and 'library' functions I've written to do certain similar things. - `Matthew <https://groups.google.com/d/msg/python-doit/eKI0uu02ZeY/cBU0RRsO0_cJ>`_

  Some time ago, I grew frustrated with Make and Ant and started porting my build files to every build tool I found (SCons, Waf, etc.). Each time, as soon as I stepped out of already available rules, I ran into some difficult to overcome stumbling blocks. Then I discovered this little gem of simplicity: doit. It's Python-based. It doesn't try to be smart, it does not try to be cool, it just works. If you are looking for a flexible little build tool for different languages and tasks, give it a chance. My build files weren't that big or complex, therefore I don't know how well it scales, and I wouldn't recommend it as a replacement for more complex build tools like Maven either. - `lelele <http://www.hnsearch.com/search#request/all&q=python-doit.sourceforge.net&start=0>`_



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

* Project management (bug tracker, feature requests and source code ) on `bitbucket <https://bitbucket.org/schettino72/doit>`_.

* `Documentation <contents.html>`_

* Questions and feedback on `google group <http://groups.google.co.in/group/python-doit>`_.

* Professional support and consulting services available from ``doit`` creator & maintainer (*schettino72* at gmail.com).

* This web site is hosted on http://sourceforge.net.

* `doit-recipes <https://bitbucket.org/schettino72/doit-recipes/wiki/Home>`_ contains a collection of non-trivial examples and a list of projects using `doit`.


Status
======

`doit` is under active development. Version 0.15 released on 2012-01.

`doit` core features are quite stable. So if there is not recent development, it does NOT mean `doit` is not being maintained... Development is done based on real world use cases. If I don't need a feature and nobody never asked for it, it is not implemented ;) It is well designed and have a very small code base so adding new features isn't hard.

If you use `doit` please drop me a line telling me your experience...
