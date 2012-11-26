
standalone script
====================

It is possible to create ``doit`` as a standalone python script including ``doit`` source code and its dependencies. This way it is easy to include this file in your project and use doit without going through the installation process.

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
