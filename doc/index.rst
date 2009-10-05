About
=====

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task. It will keep track of dependencies between "tasks" and execute them only when necessary. It was designed to be easy to use and "get out of your way".

In `doit`, unlike most (all?) build-tools, a task doesn't need to define a target file to use the execute only if not up-to-date feature. This make `doit` specially suitable for running test suites.

`doit` like most build tools is used to execute tasks defined in a configuration file. Configuration files are python modules. The tasks can be python functions or an external shell script/command. `doit` automatically keeps track of declared dependencies executing only tasks that needs to be update (based on which dependencies have changed).

If you are still wondering why someone would want to use this tool, check this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_.


Quick Start
============

install::

  $ easy_install doit

It looks like... python!

`dodo.py`

.. literalinclude:: tutorial/hello.py

run

.. code-block:: console

  eduardo@eduardo~$ doit
  hello => Cmd: echo Hello World!!! > hello.txt
	Python: function python_hello
  eduardo@eduardo~$ cat hello.txt
  Hello World!!!
  Python says Hello World!!!


Go on, read the `documentation <contents.html>`_


Project Details
===============

* This is an open-source project (`MIT license <http://opensource.org/licenses/mit-license.php>`_) written in python.

* Project management (bug tracker, feature requests and source code ) are available on `launchpad <https://launchpad.net/doit>`_.

* `Documentation <contents.html>`_

* Questions and feedback on `google group <http://groups.google.co.in/group/python-doit>`_.

* This web site is hosted on http://sourceforge.net.



Status
======

`doit` is under active development. Version 0.4 released on 2009-10.

While still a small project with room for lots of improvements and features. It is very stable and provides some great features not seen in any other project.

Development is done based on real world use cases. If I don't need a feature and nobody never asked for it, it is not implemented ;) It is well designed and have a very small code base so adding new features isn't hard.

If you use `doit` please drop me a line telling me your experience...
