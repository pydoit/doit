=============
Examples
=============

These are examples extracted from the DoIt project itself.

`doit` pre-commit
-----------------

This script is used to `pychecker <http://pychecker.sourceforge.net/>`_ and `nosetests <http://www.somethingaboutorange.com/mrl/projects/nose/>`_ on `doit` source code.

`dodo.py`:

.. literalinclude:: ../dodo.py


`doit` website
--------------

FIXME OLD

This script is used to build this website. The content is mostly written in `ReST <http://docutils.sourceforge.net/rst.html>`_ . The build script first converts the ReST to html. The generated html is inserted into the base layout given by `mako <http://www.makotemplates.org/>`_ templates.

.. literalinclude:: ../website.py
