About
=====

`doit` is a build tool that focus not only on making/building things but on executing any kind of tasks in an efficient way. Designed to be easy to use and "get out of your way".

`doit` like most build tools is used to execute tasks defined in a configuration file. Configuration files are python modules. The tasks can be python functions (or any callable) or an external shell script. `doit` automatically keeps track of declared dependencies executing only tasks that needs to be update (based on which dependencies have changed). 

In `doit`, unlike most(all?) build-tools, a task doesn't need to define a target file to use the execute only if not up-to-date feature. This make `doit` specially suitable for running test suites.

`doit` can be used to perform any task or build anything, though it doesn't support automatic dependency discovery for any language.

Project Details
===============
 
This is an open-source (`MIT license <http://opensource.org/licenses/mit-license.php>`_) written in python. Project management (bug tracker, feature requests and source code ) are available on `launchpad <https://launchpad.net/doit>`_. There is google `Discussion group <http://groups.google.co.in/group/python-doit>`_. This web site is hosted on http://sourceforge.net.

Installing
==========

Using `easy_install <http://peak.telecommunity.com/DevCenter/EasyInstall>`_::

  easy_install doit

or `download <http://pypi.python.org/pypi/doit>`_ the source and::

  pytohn setup.py install


History
=======

If you are still wondering why the world needs yet another build tool, check this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_.


