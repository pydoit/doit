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

  .. warning::

    Ubuntu packages are not maintained by core developers so they might be outdated.


  Add the doit team PPA to your system's software sources ::

    sudo add-apt-repository ppa:doit-team/ppa

  Update your package index data ::

    sudo aptitude update

  Install doit ::

    sudo aptitude install doit

  `PPA archive <https://launchpad.net/~doit-team/+archive/ppa/>`_. (`help <https://launchpad.net/+help/soyuz/ppa-sources-list.html>`_)

.. note::
  * `doit` depends on the packages `pyinotify <http://trac.dbzteam.org/pyinotify>`_ (for linux). `macfsevents <http://pypi.python.org/pypi/MacFSEvents>`_ (mac)
  * for python2.5 users `doit` depends on the packages `simplejson` and `multiprocessing`. On python 2.6 the stdlib `json` and `multiprocessing` are used.

.. warning::

   for Windows users:

   * New releases are not tested on Windows.

   * There is a bug on setuptools. Check this `bug <http://bugs.launchpad.net/doit/+bug/218276>`_ for instructions.



standalone script
====================

It is possible to create ``doit`` as a standalone python script including ``doit`` source code and its dependencies. This was it is easy to include this file in your project and use doit without going through the installation process.

Requirements
--------------

The standalone script should be created on a system where doit and dependencies are
installed. Apart from doit dependencies it also requires the the libraries "py" and "py.test".

Usage
-------

The script ``genstandalone.py`` will create a standalone 'doit' on the current working directory. So it should be executed in the path where the standalone will be distributed, i.e.::

  /my/project/path $ python ../../path/to/doit/genstandalone.py

Then you can distribute the standalone script to other systems.

.. warning::

  The generated standalone script can be used by any python version but the
  dependencies included are dependent on the python version used to generate
  the standalone script.
