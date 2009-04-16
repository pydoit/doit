About
=====

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task. It will keep track of dependencies between "tasks" and execute them only when necessary. It was designed to be easy to use and "get out of your way".

In `doit`, unlike most (all?) build-tools, a task doesn't need to define a target file to use the execute only if not up-to-date feature. This make `doit` specially suitable for running test suites.

`doit` like most build tools is used to execute tasks defined in a configuration file. Configuration files are python modules. The tasks can be python functions or an external shell script/command. `doit` automatically keeps track of declared dependencies executing only tasks that needs to be update (based on which dependencies have changed). 

If you are still wondering why someone would want to use this tool, check this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_.


Project Details
===============
 
* This is an open-source project (`MIT license <http://opensource.org/licenses/mit-license.php>`_) written in python. 

* Project management (bug tracker, feature requests and source code ) are available on `launchpad <https://launchpad.net/doit>`_. 

* Questions and feedback on `google group <http://groups.google.co.in/group/python-doit>`_. 

* This web site is hosted on http://sourceforge.net.

Installing
==========

* Using `easy_install <http://peak.telecommunity.com/DevCenter/EasyInstall>`_::

  $ easy_install doit

* `Download <http://pypi.python.org/pypi/doit>`_ the source and::

  $ pytohn setup.py install

* Get latest development version::

  $ bzr branch lp:doit
