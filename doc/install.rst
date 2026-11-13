.. meta::
   :description: How-to install pydoit using pip, from source or OS package
   :keywords: python, doit, install, git, github, ubuntu, linux, windows

.. title:: pydoit package installation options

==========
Installing
==========


pip
^^^

`package <https://pip.pypa.io/>`_ (requires Python 3.10+)::

   $ pip install doit


Source
^^^^^^

Download `source <https://pypi.python.org/pypi/doit>`_::

  $ pip install .


git repository
^^^^^^^^^^^^^^

Get latest development version::

  $ git clone https://github.com/pydoit/doit.git
  $ cd doit
  $ pip install .

For a development setup see ``DEV-README.rst`` in the repository.


OS package
^^^^^^^^^^

Several distributions include native `doit` packages.
`Repology.org <https://repology.org/project/doit/versions>`_
provides up-to-date information about available packages and
`doit` versions on each distribution.

Anaconda
^^^^^^^^

`doit` is also packaged on `Anaconda <https://anaconda.org/conda-forge/doit>`_.
Note this is not an official package and might be outdated.
