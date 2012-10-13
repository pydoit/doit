================
README
================


doit - automation tool
======================

`doit` comes from the idea of bringing the power of build-tools to
execute any kind of task

see doc/index.rst or `website <http://python-doit.sourceforge.net/>`


Project Details
===============

 - Project management on `bitbucket <https://bitbucket.org/schettino72/doit>`_
 - Website http://python-doit.sourceforge.net/
 - `Discussion group <http://groups.google.co.in/group/python-doit>`_


license
=======

The MIT License
Copyright (c) 2008-2012 Eduardo Naufel Schettino

see LICENSE file


developers / contributors
==========================

see AUTHORS file


install
=======

doit is tested on python 2.5, 2.6, 2.7, 3.2.

``python setup.py install``


dependencies
=============

- simplejson [python 2.5]
- multiprocessing [python 2.5]
- pyinotify (linux) [all python versions]
- macfsevents (mac)

Tools required for development:

- merucrial * VCS
- py.test * unit-tests
- mock * unit-tests
- coverage * code coverage
- epydoc * API doc generator
- sphinx * doc tool
- pyflakes * syntax checker


tests
=======

You can use a standalone script::

  python runtests.py

or use `py.test <http://codespeak.net/py/dist/test/index.html>`_ ::

  py.test



developemnt setup
==================

The best way to setup an environment to develop `doit` itself is to
create a virtualenv...::

  doit$ virtualen dev
  (dev)doit$ dev/bin/activate

install `doit` as "editable", and add development dependencies
from `dev_requirements.txt`::

  (dev)doit$ pip install --editable .
  (dev)doit$ pip install --requirement dev_requirements.txt


documentation
=============

``doc`` folder contains ReST documentation based on Sphinx.

``doit/doc$ make html``

They are the base for creating the website. The only difference is
that the website includes analytics tracking using Pwiki.
To create it (after installing doit):

``doit website``

The website will also includes epydoc generated API documentation.


