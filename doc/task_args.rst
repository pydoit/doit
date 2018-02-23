
Passing Task Arguments from the command line
============================================

.. _parameters:

arguments
-----------

It is possible to pass option parameters to the task through the command line.

Just add a ``params`` field to the task dictionary. ``params`` must be a list of
dictionaries where every entry is an option parameter. Each parameter must
define a name, and a default value. It can optionally define a "short" and
"long" names to be used from the command line (it follows unix command line
conventions). It may also specify additional attributes, such as
`type` and `help` (see :ref:`below <parameters-attributes>`).


See the example:

.. literalinclude:: samples/parameters.py


For python-actions the python function must define arguments with the same name as a task parameter.

.. code-block:: console

    $ doit py_params -p abc --param2 4
    .  py_params
    abc
    9

Need a list in your python function? Specify an option with ``type``
set to ``list``.

.. code-block:: console

    $ doit py_params_list -l milk -l eggs -l bread
    .  py_params_list
    milk
    eggs
    bread

Choices can be set by specifying an option with ``choices`` set to a
sequence of a 2-element tuple.
The first element is the choice value.
The second element is the choice description,
if not required, use an empty string.

.. code-block:: console

    $ doit py_params_choice -c that
    .  py_params_choice
    that

Invalid choices are detected and passed back to the user.

.. code-block:: console

    $ doit py_params_choice -c notavalidchoice
    ERROR: Error parsing parameter 'choice'. Provided 'notavalidchoice' but available choices are: 'this', 'that'.


For cmd-actions use python string substitution notation:

.. code-block:: console

    $ doit cmd_params -f "-c --other value"
    .  cmd_params
    mycmd -c --other value xxx



.. _parameters-attributes:

All parameters attributes
^^^^^^^^^^^^^^^^^^^^^^^^^

Here is the list of all attributes ``param`` accepts:

``name``
    Name of the parameter, identifier used as name of the the parameter
    on python code.
    It should be unique among others.

    :required:  True
    :type:      `str`

``default``
    Default value used when it is set through command-line.

    :required:  True

``short``
    Short parameter form, used for e.g. ``-p value``.

    :required:  optional
    :type:      `str`

``long``
    Long parameter form, used for e.g. ``--parameter value``.

    :required:  optional
    :type:      `str`

``type``
    Actually it can be any python callable.
    It coverts the string value received from command line to whatever
    value to be used on python code.

    If the ``type`` is ``bool`` the parameter is treated as an *option flag*
    where no value should be specified, value is set to ``True``.
    Example: ``doit mytask --flag``.

    :required:  optional
    :type:      `callable` (e.g. a `function`)
    :default:   `str`

``choices``
    List of accepted value choices for option.
    First tuple element is the value name,
    second tuple element is a help description for value.

    :required: optional
    :type: list of 2-tuple strings

``help``
    Help message associated to this parameter, shown when
    :ref:`help <cmd-help>` is called for this task,
    e.g. ``doit help mytask``.

    :required:  optional
    :type:      `str`

``inverse``
    [only for `bool` parameter]
    Set inverse flag long parameter name, value will be set to ``False``
    (see example below).

    :required:  optional
    :type:      `str`

    Example, given following code:

    .. literalinclude:: samples/parameters_inverse.py

    calls to task `with_flag` show flag on or off:

    .. code-block:: console

        $ doit with_flag
        .  with_flag
        Flag On
        $ doit with_flag --flagoff
        .  with_flag
        Flag Off


positional arguments
------------------------

Tasks might also get positional arguments from the command line
as standard unix commands do,
with positional arguments *after* optional arguments.

.. literalinclude:: samples/pos.py

.. code-block:: console

    $ doit pos_args -p 4 foo bar
    .  pos_args
    param1 is: 4
    positional-0: foo
    positional-1: bar


.. warning::

   If a task accepts positional arguments, it is not allowed to pass
   other tasks after it in the command line. For example if `task1`
   takes positional arguments you can not call::

     $ doit task1 pos1 task2

   As the string `task2` would be interpreted as positional argument from
   `task1` not as another task name.




.. _command line variables:

command line variables (*doit.get_var*)
-----------------------------------------

It is possible to pass variable values to be used in dodo.py from the command line.

.. literalinclude:: samples/get_var.py

.. code-block:: console

    $ doit
    .  echo
    hi {abc: NO}
    $ doit abc=xyz x=3
    .  echo
    hi {abc: xyz}
