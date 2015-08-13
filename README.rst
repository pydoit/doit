================
README
================

.. display some badges

.. image:: https://img.shields.io/pypi/v/doit.svg
        :target: https://pypi.python.org/pypi/doit

.. image:: https://img.shields.io/pypi/dm/doit.svg
        :target: https://pypi.python.org/pypi/doit

.. image:: https://travis-ci.org/pydoit/doit.png?branch=master
    :target: https://travis-ci.org/pydoit/doit

.. image:: https://ci.appveyor.com/api/projects/status/f7f97iywo8y7fe4d/branch/master?svg=true
    :target: https://ci.appveyor.com/project/schettino72/doit/branch/master

.. image:: https://coveralls.io/repos/pydoit/doit/badge.png?branch=master
  :target: https://coveralls.io/r/pydoit/doit?branch=master


.. image:: https://badges.gitter.im/Join%20Chat.svg
  :alt: Join the chat at https://gitter.im/pydoit/doit
  :target: https://gitter.im/pydoit/doit?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


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
 - Plugins, extensions and projects based on doit - https://github.com/pydoit/doit/wiki/powered-by-doit

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

.. note::

    Windows developers: Due to a  bug in `wheel` distributions
    `pytest` must not be installed from a `wheel`.

    e.g.::

      pip install pytest --no-use-wheel

    See for more information:

      - https://github.com/pytest-dev/pytest/issues/749
      - https://bitbucket.org/pytest-dev/pytest/issues/749/


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


profiling
---------

::

  python -m cProfile -o output.pstats `which doit` list

  gprof2dot -f pstats output.pstats | dot -Tpng -o output.png

contributing
==============

On github create pull requests using a named feature branch.


