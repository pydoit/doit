==================
Environment setup
==================

Some tasks require some kind of environment setup/cleanup. Tasks have a list of "setup" objects. These objects can optionally define a "setup" and a "cleanup" method. Multiple tasks can share the same setup object.

* the setup method will be executed before the first task that uses this object is executed
* if no task that uses this object is called it is never setup
* if the setup method has already been called it won't be executed again for a different task
* the cleanup method is executed after all tasks have finished their execution.

Example:

.. literalinclude:: tutorial/setup.py

