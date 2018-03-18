==========
Installing
==========


pip
^^^

`package <http://pip.pypa.io/>`_::

   $ pip install doit

Latest version of `doit` supports only python 3.
If you are using python 2::

  $ pip install "doit<0.30"

Source
^^^^^^

Download `source <http://pypi.python.org/pypi/doit>`_::

  $ pip install -e .


git repository
^^^^^^^^^^^^^^

Get latest development version::

  $ git clone https://github.com/pydoit/doit.git


OS package
^^^^^^^^^^

Several distributions include native `doit` packages.
`Repology.org <https://repology.org/metapackage/doit/badges>`_
provides up-to-date information about available packages and
`doit` versions on each distribution.

Anaconda
^^^^^^^^

`doit` is also packaged on `Anaconda <https://anaconda.org/conda-forge/doit>`_.
Note this is not an official package and might be outdated.


.. note::
  * `doit` depends on the packages
    `pyinotify <http://trac.dbzteam.org/pyinotify>`_ (for linux),
    `macfsevents <http://pypi.python.org/pypi/MacFSEvents>`_ (mac).
