================
README
================

.. display some badges

.. image:: https://pypip.in/v/doit/badge.png
        :target: https://pypi.python.org/pypi/doit

.. image:: https://pypip.in/d/doit/badge.png
        :target: https://pypi.python.org/pypi/doit

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

 - Source code & Project management on bitbucket - https://bitbucket.org/schettino72/doit
 - Website & docs - http://pydoit.org
 - Discussion group - https://groups.google.com/forum/#!forum/python-doit
 - Official github mirror at - https://github.com/pydoit/doit

license
=======

The MIT License
Copyright (c) 2008-2013 Eduardo Naufel Schettino

see LICENSE file


developers / contributors
==========================

see AUTHORS file


install
=======

*doit* is tested on python 2.6, 2.7, 3.2, 3.3, 3.4.

::

 $ python setup.py install


dependencies
=============

- six
- pyinotify (linux)
- macfsevents (mac)

Tools required for development:

- mercurial * VCS
- py.test * unit-tests
- mock * unit-tests
- coverage * code coverage
- epydoc * API doc generator
- sphinx * doc tool
- pyflakes * syntax checker


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

You can use the standalone script::

  $ python runtests.py

or use py.test - http://pytest.org

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


contributing
==============

On bitbucket create pull requests on ``default`` branch.

On github create pull requests using a named feature branch.


github mirror setup
=====================

This is only needed if you will manage both upstream in github and bitbucket.
For using github only just use `git` normally and ignore it is a mirror.

* install hg-git (http://hg-git.github.io/) ``sudo pip install hg-git``.

* enable the extension. on ``~/.hgrc``::

    [extensions]
    hggit =

* add a named path ``github`` on ``doit/.hg/hgrc``::

    [paths]
    default = https://bitbucket.org/schettino72/doit
    github = git+ssh://git@github.com/pydoit/doit.git

* make sure you have a ssh key registered on github ::

   $ hg push github

