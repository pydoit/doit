=======
FAQ
=======

*doit* is too verbose, why don't you use decorators?
-----------------------------------------------------

With decorators:

.. code-block:: python

   from doit.i_dont_exist import decorators

   @decorators.dependencies('a','b')
   @decorators.task
   def task_mytask():
      x = 1
      y = 2
      z = 3

Without decorators:

.. code-block:: python

   def task_mytask():
      def the_action():
	  x = 1
	  y = 2
	  z = 3

      return {'actions': [the_action],
	      'dependencies': ['a','b']}


* not sure I stack the decorators in the correct order :P

* using decorators is *one* line shorter ( but i am not counting the import line). not a big saver in terms of verbosity at all.

* you need to import the decorator

* decorators were created to change the behavior of functions. Of course it can do other stuff but it is an overkill. Decorators may look *cool* but are much harder understand, code and debug.

* we can not replace the dictionaries syntax because it is more powerful that using decorators. The implementation is also simpler.

* There should be one -- and preferably only one -- obvious way to do it. (zen of python)
