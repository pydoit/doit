================
README
================

.. display some badges

.. image:: https://pypip.in/v/doit/badge.png
        :target: https://pypi.python.org/pypi/doit

.. image:: https://pypip.in/d/doit/badge.png
        :target: https://pypi.python.org/pypi/doit

.. disable this until i figure out how to debug unstable tests
  .. image:: https://travis-ci.org/pydoit/doit.png?branch=master
    :target: https://travis-ci.org/pydoit/doit

.. image:: https://coveralls.io/repos/pydoit/doit/badge.png?branch=master
  :target: https://coveralls.io/r/pydoit/doit?branch=master


doit - automation tool
======================

*doit* comes from the idea of bringing the power of build-tools to
execute any kind of task


Project Details
===============

 - Website & docs - http://pydoit.org
 - Project management on github - https://github.com/pydoit/doit
 - Discussion group - https://groups.google.com/forum/#!forum/python-doit
 - News/twitter - https://twitter.com/py_doit

license
=======

The MIT License
Copyright (c) 2008-2015 Eduardo Naufel Schettino

see LICENSE file


developers / contributors
==========================

see AUTHORS file


install
=======

*doit* is tested on python 2.7, 3.3, 3.4.

::

 $ python setup.py install


dependencies
=============

- six
- pyinotify (linux)
- macfsevents (mac)
- configparser (python2 only - backport of py3 configparser)

Tools required for development:

- git * VCS
- py.test * unit-tests
- mock * unit-tests
- coverage * code coverage
- epydoc * API doc generator
- sphinx * doc tool
- pyflakes * syntax checker
- doit-py * helper to run dev tasks


development setup
==================

The best way to setup an environment to develop *doit* itself is to
create a virtualenv...

::

  doit$ virtualenv dev
  (dev)doit$ dev/bin/activate

install ``doit`` as "editable", and add development dependencies
from `dev_requirements.txt`::

  (dev)doit$ pip install --editable .
  (dev)doit$ pip install --requirement dev_requirements.txt



tests
=======

Use py.test - http://pytest.org

::

  $ py.test



documentation
=============

``doc`` folder contains ReST documentation based on Sphinx.

::

 doc$ make html

They are the base for creating the website. The only difference is
that the website includes analytics tracking.
To create it (after installing *doit*)::

 $ doit website

The website will also includes epydoc generated API documentation.


spell checking
--------------

All documentation is spell checked using the task `spell`::

  $ doit spell

It is a bit annoying that code snippets and names always fails the check,
these words must be added into the file `doc/dictionary.txt`.

The spell checker currently uses `hunspell`, to install it on debian based
systems install the hunspell package: `apt-get install hunspell`.


contributing
==============

On github create pull requests using a named feature branch.


