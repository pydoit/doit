===========
DEV-README
===========

developers / contributors
==========================

see AUTHORS file


development setup
==================

Dev dependencies are defined as ``[dependency-groups]`` in ``pyproject.toml``.

Using `uv <https://docs.astral.sh/uv/>`_ (same as CI):

.. code:: bash

  uv sync --group dev --group docs

Using pip (requires pip >= 25.1):

.. code:: bash

  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install --editable . --group dev --group docs


using an unreleased rut
-----------------------

To test against a local checkout of rut (e.g. ``../rut``),
install it on top of the dev dependencies.

pip:

.. code:: bash

  pip install --editable ../rut

uv:

.. code:: bash

  uv pip install --editable ../rut
  uv run --no-sync rut

Note: a plain ``uv sync`` or ``uv run`` re-installs rut from PyPI.


tests
=======

Use rut - https://pypi.org/project/rut/

.. code:: bash

  $ rut


linting
=======

.. code:: bash

  $ doit pyflakes
  $ doit codestyle


documentation
=============

``doc`` folder contains ReST documentation based on Sphinx.

.. code:: bash

 doc$ make html

They are the base for creating the website. The only difference is
that the website includes analytics tracking.
To create it (after installing *doit*):

.. code:: bash

 $ doit website


website deployment
------------------

The website (pydoit.org) is served by GitHub Pages from a **separate repo**:
`schettino72/doit-website <https://github.com/schettino72/doit-website>`_
(``gh-pages`` branch, default ``pages-build-deployment`` workflow).

The CI workflow in this repo (``.github/workflows/website.yml``) builds
the site and uploads it as an artifact — it does **not** deploy.
Deployment is manual:

.. code:: bash

  # 1. Build the website and copy to ../doit-website
  $ doit website_update

  # 2. Commit and push from the website repo
  $ cd ../doit-website
  $ git add -A && git commit -m "update site"
  $ git push

The ``website_update`` task builds the site, rsyncs to ``../doit-website``,
and writes ``CNAME`` and ``.nojekyll`` files.

This keeps deployment intentionally decoupled from doc changes,
allowing work-in-progress docs without publishing them.



spell checking
--------------

All documentation is spell checked using the task `spell`:

.. code:: bash

  $ doit spell

It is a bit annoying that code snippets and names always fails the check,
these words must be added into the file `doc/dictionary.txt`.

The spell checker currently uses `hunspell`, to install it on debian based
systems install the hunspell package: `apt-get install hunspell`.


profiling
---------

.. code:: bash

  python -m cProfile -o output.pstats `which doit` list

  gprof2dot -f pstats output.pstats | dot -Tpng -o output.png


releases
========

Update version number at:

- doit/version.py
- pyproject.toml
- doc/conf.py

.. code:: bash

   python -m build
   twine upload dist/doit-X.Y.Z.tar.gz
   twine upload dist/doit-X.Y.Z-py3-none-any.whl

Remember to push GIT tags::

  git push --tags
