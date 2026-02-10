===========
DEV-README
===========

developers / contributors
==========================

see AUTHORS file


development setup
==================

Create a virtualenv and install in editable mode with dev dependencies:

.. code:: bash

  python -m venv .venv
  source .venv/bin/activate
  pip install --editable .
  pip install --requirement dev_requirements.txt


tests
=======

Use py.test - https://pytest.org

.. code:: bash

  $ py.test


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
