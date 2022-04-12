.. meta::
   :description: Configuring pydoit with TOML and INI files
   :keywords: python, doit, documentation, guide, configuration, ini, toml

.. title:: Configuration with TOML and INI files  - pydoit guide


Configuration
=============


config param names
------------------

Note that the configuration option's name is not always the same as the
*long* argument name used in the command line.

I.e. To specify dodo file other than `dodo.py` from the command line
you specify the option as ``-f`` or ``--file``, but from a config file
it is called ``dodoFile``.

The name can be seem from ``doit help`` output::

   -f ARG, --file=ARG        load task from dodo FILE [default: dodo.py]  (config: dodoFile)


pyproject.toml
--------------

`doit` configuration can be read from `pyproject.toml <https://www.python.org/dev/peps/pep-0518/>`_
under the `tool.doit` namespace.
This is the preferred configuration source, and may gain features not available in the legacy `doit.cfg`.

.. note::

   A TOML parser (`tomllib <https://docs.python.org/3.11/library/tomllib.html>`_)
   is part of the standard library since Python 3.11.
   For earlier Python versions, a third-party package is required, one of:

   - `tomli <https://pypi.org/project/tomli/>`_
   - `tomlkit <https://pypi.org/project/tomlkit/>`_


TOML vs INI
^^^^^^^^^^^

While mostly similar, `TOML <https://toml.io>`_ differs from the INI format
in a few ways:

- all strings must be quoted with `'` or `"`
- triple-quoted strings may contain new line characters (`\n`) and quotes
- must be saved as UTF-8
- integers and floating point numbers can be written without quotes
- boolean values can be written unquoted and lower-cased, as `true` and `false`

Unlike "plain" TOML, `doit` will parse pythonic strings into their correct types,
e.g. `"True"`, `"False"`, `"3"`, but using "native" TOML types may be preferable.


tool.doit
^^^^^^^^^

The `tool.doit` section may contain command line options that will be used
(if applicable) by any commands.

Example setting the DB backend type:

.. code-block:: toml

   [tool.doit]
   backend = "json"

All commands that have a `backend` option (*run*, *clean*, *forget*, etc),
will use this option without the need for this option in the command line.


tool.doit.commands
^^^^^^^^^^^^^^^^^^

To configure options for a specific command, use a section with
the command name under `tool.doit.commands`:

.. code-block:: toml

   [tools.doit.commands.list]
   status = true
   subtasks = true


tool.doit.plugins
^^^^^^^^^^^^^^^^^

Check the :ref:`plugins <plugins>` section for an introduction
on available plugin categories.


tool.doit.tasks
^^^^^^^^^^^^^^^

To configure options for a specific task, use a section with
the task name under `tool.doit.tasks`:

.. code-block:: toml

   [tool.doit.tasks.make_cookies]
   cookie_type = "chocolate"
   temp = "375F"
   duration = 12


doit.cfg
--------

`doit` also supports an INI style configuration file
(see `configparser <https://docs.python.org/3/library/configparser.html>`_).
Note: key/value entries can be separated only by the equal sign `=`.

If a file name `doit.cfg` is present in the current working directory,
it is processed. It supports 4 kind of sections:

- a `GLOBAL` section
- a section for each plugin category
- a section for each command
- a section for each task


GLOBAL section
^^^^^^^^^^^^^^

The `GLOBAL` section may contain command line options that will
be used (if applicable) by any commands.

Example setting the DB backend type:

.. code-block:: ini

 [GLOBAL]
 backend = json

All commands that have a `backend` option (*run*, *clean*, *forget*, etc),
will use this option without the need for this option in the command line.


commands section
^^^^^^^^^^^^^^^^

To configure options for a specific command, use a section with
the command name:

.. code-block:: ini

 [list]
 status = True
 subtasks = True


plugins sections
^^^^^^^^^^^^^^^^

Check the :ref:`plugins <plugins>` section for an introduction
on available plugin categories.


per-task sections
^^^^^^^^^^^^^^^^^

To configure options for a specific task, use a section with
the task name prefixed with "task:":

.. code-block:: ini

 [task:make_cookies]
 cookie_type = chocolate
 temp = 375F
 duration = 12


configuration at *dodo.py*
--------------------------

As a convenience you can also set `GLOBAL` options directly into a `dodo.py`.
Just put the option in the `DOIT_CONFIG` dict.
This example below sets the default tasks to be run, the ``continue`` option,
and a different reporter.

.. literalinclude:: samples/doit_config.py

So if you just execute

.. code-block:: console

   $ doit

it will have the same effect as executing

.. code-block:: console

   $ doit --continue --reporter json my_task_1 my_task_2


.. note::

  Not all options can be set on `dodo.py` file.
  The parameters ``--file`` and ``--dir`` can not be used on config because
  they control how the *dodo* file itself is loaded.

  Also if the command does not read the `dodo.py` file it obviously will
  not be used.
