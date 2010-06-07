==========
Installing
==========

* Using `pip <http://pip.openplans.org/>`_ or `easy_install <http://peak.telecommunity.com/DevCenter/EasyInstall>`_::

  $ pip install doit
  $ easy_install doit

* `Download <http://pypi.python.org/pypi/doit>`_ the source and::

  $ python setup.py install

* Get latest development version::

  $ bzr branch lp:doit

* Ubuntu packages

  Add the following line to your system's software sources ::

    deb http://ppa.launchpad.net/doit-team/ppa/ubuntu karmic main

  `PPA archive <https://launchpad.net/~doit-team/+archive/ppa/>`_. (`help <https://launchpad.net/+help/soyuz/ppa-sources-list.html>`_)

.. note::
  * `doit` dependends on the packages `pyinotify <http://trac.dbzteam.org/pyinotify>`_ (for linux). `macfsevents <http://pypi.python.org/pypi/MacFSEvents>`_ (mac)
  * for python2.4 and python2.5 users `doit` depends on the packages `simplejson` and `multiprocessing`. On python 2.6 the stdlib `json` and `multiprocessing` are used.

.. warning::

   for Windows users:

   * New releases are not tested on Windows.

   * There is a bug on setup tools. Check this `bug <http://bugs.launchpad.net/doit/+bug/218276>`_ for instructions.

