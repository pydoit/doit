==========
Installing
==========

* Using `pip <http://pip.openplans.org/>`_ or `easy_install <http://peak.telecommunity.com/DevCenter/EasyInstall>`_::

  $ pip install doit
  $ easy_install doit

* `Download <http://pypi.python.org/pypi/doit>`_ the source and::

  $ python setup.py install

* Get latest development version::

  $ hg clone https://bitbucket.org/schettino72/doit


.. note::
  * `doit` depends on the packages `pyinotify <http://trac.dbzteam.org/pyinotify>`_ (for linux). `macfsevents <http://pypi.python.org/pypi/MacFSEvents>`_ (mac)
  * for python2.5 users `doit` depends on the packages `simplejson` and `multiprocessing`. On python 2.6 the stdlib `json` and `multiprocessing` are used.

.. warning::

   for Windows users:

   * New releases are not tested on Windows.

   * There is a bug on setuptools. Check this `bug <http://bugs.launchpad.net/doit/+bug/218276>`_ for instructions.
