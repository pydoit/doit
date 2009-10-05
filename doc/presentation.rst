.. include:: <s5defs.txt>

======================================================================
doit: bringing the power of build tools to execute any kind of task
======================================================================


"Anything worth repeating is worth automating"


:Author: Eduardo Schettino


build tools
============

Tools that manage repetitive tasks and their dependencies


* 1977: Make
* C & other compiled languages



Make - how it works
===================

* rules


target: dependencies ...
        commands
        ...

* simple (and fragile) dependency checking (timestamps)


Make - how does it look?
========================

.. class:: tiny
.. sourcecode:: make

   helloworld: helloworld.o
	   cc -o $@ $<

   helloworld.o: helloworld.c
	   cc -c -o $@ $<

   .PHONY: clean
   clean:
	   rm -f helloworld helloworld.o

Make - problems
===============

* Make is not a programming language (how can I do a loop?)
* compact syntax (but hard to understand and remember)
* hard to debug


other build tools
==================

* CMake
* java/XML: ant, maven
* Rake
* SCons


dynamic languages
=================

* who needs a build tool?
* unit-test

*web development*

* heavy use of database
* tests on browsers are slow
* need environment setup (start servers, reset DB...)


doit - design
=============

* nice language => python
* get out of your way
* we-don't-need-no-stinking-API (learned from pytest)
* dependencies by task not on file/targets (unique feature)

doit - do what?
================


it's up to you!

doit is a tool to help you execute **your** tasks in a effecient way.


doit - how it works
===================

* actions => what the task does

  * python (portable)
  * shell commands (fast, easy to use other programs)

* targets => what this task creates

* dependencies => what this task uses as input


doit - how does it look? (1)
============================

.. class:: tiny
.. sourcecode:: python

   DEFAULT_TASKS = ['edit']

   # map source file to dependencies
   SOURCE = {
       'main': ["defs.h"],
       'kbd': ["defs.h command.h"],
       'command': ["defs.h command.h"],
       'display': ["defs.h buffer.h"],
       'insert': ["defs.h buffer.h"],
       'files': ["defs.h buffer.h command.h"],
       }

   OBJECTS = ["%s.o" module for module in SOURCE.iterkeys()]


doit - how does it look? (2)
============================

.. class:: tiny
.. sourcecode:: python

   def task_edit():
       return {'actions': ['cc -o edit %s' % " ".join(OBJECTS)],
	       'dependencies': OBJECTS,
	       'targets': ['edit']
	       }

   def task_object():
       for module, dep in SOURCE.iteritems():
	   dependencies = dep + ['%s.c' % module]
	   yield {'name': module,
		  'actions': ["cc -c %s.c" % module]
		  'targets': ["%s.o" % module],
		  'dependencies': dependencies,
		  }


doit - how does it look? (3)
============================

.. class:: tiny
.. sourcecode:: python

   import os
   def task_clean():
       for f in ['edit'] + OBJECTS:
	   yield {'name': f,
                  'actions': [(os.remove, f)],
		  'dependencies': [f]}



doit - no targets
=================

.. class:: tiny
.. sourcecode:: python

  import glob;

  pyFiles = glob.glob('*.py')

  def task_checker():
      for f in pyFiles:
	  yield {'actions': ["pychecker %s"% f],
		 'name':f,
		 'dependencies':(f,)}


doit - run once
===============

.. class:: tiny
.. sourcecode:: python

   URL = "http://svn.dojotoolkit.org/src/util/trunk/shrinksafe/shrinksafe.jar"
   shrinksafe = "shrinksafe.jar"

   jsFile = "file1.js"
   compFile = "compressed1.js"

   def task_shrink():
       return {'actions': ['java -jar %s %s > %s'% (shrinksafe, jsFile, compFile)],
	       'dependencies': [shrinksafe]
	       }

   def task_get_shrinksafe():
       return {'actions': ["wget %s"% URL],
	       'targets': [shrinksafe],
	       'dependencies': [True]
	       }


doit - groups
=============

.. class:: tiny
.. sourcecode:: python

   def task_foo():
       return {'actions': ["echo foo"]}

   def task_bar():
       return {'actions': ["echo bar"]}

   def task_mygroup():
       return {'actions': None,
	      'dependencies': [':foo', ':bar']}


doit - environment setup (1)
============================

.. class:: tiny
.. sourcecode:: python

   ### task setup env. good for functional tests!

   class SetupSample(object):
       def __init__(self, server):
	   self.server = server

       def setup(self):
	   # start server
	   pass

       def cleanup(self):
	   # stop server
	   pass


doit - environment setup (2)
============================

.. class:: tiny
.. sourcecode:: python

   setupX = SetupSample('x')
   setupY = SetupSample('y')

   def task_withenvX():
       for fin in ('a','b','c'):
	   yield {'name': fin,
		  'actions':['echo x'],
		  'setup': setupX}

   def task_withenvY():
       return {'actions': ['echo x'],
	       'setup': setupY}


doit - cmd line
===============

* run
* list
* forget


doit - future
=============

* community > 1
* support clean task
* command line parameters
* specific support for common tasks (C compilation)
* dependency scanners
* speed improvements


thanks
===========

Questions?


doit website: http://python-doit.sourceforge.net


references:
http://software-carpentry.org/
http://www.gnu.org/software/make/

presentation written in ReST/rst2s5 + pygments
