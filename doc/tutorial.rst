===========
Tutorial
===========

Tasks
-----

`doit` is all about automation of tasks execution. Tasks are external shell commands/scripts or a python function (or any callable). So a task can be anything you can code :)

Configuration files (aka dodo file) are written in python. You should be comfortable with python basics. If you don't know python yet check `Python tutorial <http://docs.python.org/tut/>`_ and `Dive Into Python <http://www.diveintopython.org/>`_. 

``tutorial_01.py``
::

  def say_hello():
      output = open("hello_python.txt","w")
      output.write("Hello World.")
      output.close()    
      return True


  def task_hello_python():
      return {'action':say_hello}

  def task_hello_sh():
      return {'action':"echo 'Hello World' > hello_sh.txt"}


Any function that start with the string ``task_`` is a task. A task must return a dictionary where it specifies its parameters. The only required parameter is ``action``.

Cmd-Task
  If ``action`` is a string it will be executed by the shell. 
  The result of the task follows the shell convention. If the process exit with the value ``0`` it is successful.  Any other value means the task failed.

Python-Task
  If ``action`` is a function reference (or any callable) the python function is executed. 
  The result of the task is given by the returned value of the ``action`` function. So it **must** return a value that evaluates to True to indicate successful completion of the task.

After executing the command below you should get the two files with the "Hello World" text.

::

  .../tutorial$ doit -f tutorial_01.py
  hello_python => Python: function say_hello
  hello_sh => Cmd: echo 'Hello World' > hello_sh.txt
  


Task arguments
----------------

You can pass arguments to your Python-Task *action* function using the optional fields ``args`` (sequence) and ``kwargs`` (dictionary). They will be passed as `*args <http://docs.python.org/tut/node6.html#SECTION006730000000000000000>`_ and `**kwargs <http://docs.python.org/tut/node6.html#SECTION006720000000000000000>`_ to the *action* function.

For Cmd-Task, just manipulate the string!


``tutorial_02.py``
::

  def say_something(times, text):
      output = open("hey_python.txt","w")
      for x in range(times):
	  output.write(text)
      output.close()    
      return True


  def task_hey_python():
      return {'action':say_something,
	      'args':(10,),
	      'kwargs':{'text':'hey! '}}

  def task_hi_sh():
      hi = 10*"hi! "
      return {'action':"echo '%s' > hi_sh.txt"% hi}



Dependencies & Targets
----------------------

Dependency
  A *dependency* indicates that the task depends on it to be executed. 

  i.e. A 'C' object file depends on the source code file to execute the compilation.
  Dependencies are generally on files. But `doit` also handle dependencies on other tasks.

Target
  A task *target* is the result produced by the task execution.

  i.e. An object file from a compilation task.


``Dependencies`` and ``targets`` are optional fields for the task dictionary. They must be a sequence of strings.

`doit` automatically keeps track of task dependencies. It saves the signature (MD5) of the dependencies every time the task is completed successfully. In case there is no modification in the dependencies (and targets) files it skip the task execution to save time as it would produce the same output from the previous run. Tasks without dependencies are always executed.

Dependencies are on tasks not on targets, so a task even without defining targets can take advantage of the execute only if not up-to-date feature.

Targets are basically treated as dependencies. The only difference is that if a dependency file is not on the file system an error is raised. While targets are not required to exist on the file system before the task is executed.


Example 1 - Simple Dependency - Lint
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose you want to apply a lint-like tool(`PyChecker <http://pychecker.sourceforge.net/>`_) to your source code file. You can define the source code as a dependency to the task.

``checker.py``
::

  pyfile = "sample.py"
  def task_checker():
      return {'action': "pychecker %s"% pyfile, 
	      'dependencies':(pyfile,)}

This way the Pychecker is executed only when source file has changed. On the output the string ``---`` preceding the task description indicates the task execution was skipped because it is up-to-date.

::

  .../tutorial$ doit -f checker.py 
  checker => Cmd: pychecker sample.py
  .../tutorial$ doit -f checker.py 
  --- checker => Cmd: pychecker sample.py


Example 2 - Target + Dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You might be thinking... Why should I define targets if the task itself can keep track of dependencies? There are two reasons to define targets.

#. Even if the dependencies do not change but the target is modified the task is executed again. i.e. if you manually edit a file built by a `doit` task it will be rebuilt if you execute the task even the are no modifications on the dependencies.

#. In case the target file is a dependency for another file it ensure tasks will be executed on the proper order. (By default tasks are executed in the order they were defined).

In the next example the task "count_lines" is used to create a file reporting the number of lines from "files.txt". "files.txt" is actually the target from another task.

``counter.py``
::

  def task_count_lines():
      return {'action': "wc -l files.txt > count.txt",
	      'dependencies':['files.txt'],
	      'targets':['count.txt']}

  def task_ls():
      return {'action':"ls -1 > files.txt",
	      'targets':['files.txt']}


::

  .../tutorial$ doit -f counter.py
  ls => Cmd: ls -1 > files.txt
  count_lines => Cmd: wc -l files.txt > count.txt

Notice that "task_ls" is executed before "task_count_line" even that it was defined after. Because its target is a dependency of "task_count_line".

Also notice that even that "task_ls" is always executed (because it doesn't define any dependency). "task_count_lines" is executed only if "files.txt" is change.

 
To define a dependency on another task use the task name (whatever comes after ``task_`` on the function name) preceded by ":". This is only to ensure the correct order of the task execution. In this case both tasks would be always executed.

``counter2.py``
::

  def task_count_lines():
      return {'action': "wc -l files.txt > count.txt",
	      'dependencies':[':ls'],
	      'targets':['count.txt']}

  def task_ls():
      return {'action':"ls -1 > files.txt",
	      'targets':['files.txt']}


Subtasks
--------

Most of the time we want to apply the same task several times in different contexts. 

The task function can return a generator that yields dictionaries. Since each subtask must be uniquely identified it requires an additional field ``name``. 

Below an example on how to execute PyChecker for all files in a folder.

``checker2.py``
::

  import glob;

  pyFiles = glob.glob('*.py')

  def task_checker():
      for f in pyFiles:
	  yield {'action': "pychecker %s"% f, 
		 'name':f, 
		 'dependencies':(f,)}


Output::

  .../tutorial$ doit -f checker2.py 
  checker:tutorial_01.py => Cmd: pychecker tutorial_01.py
  checker:tutorial_02.py => Cmd: pychecker tutorial_02.py
  checker:sample.py => Cmd: pychecker sample.py
  checker:checker.py => Cmd: pychecker checker.py
  checker:counter.py => Cmd: pychecker counter.py
  checker:counter2.py => Cmd: pychecker counter2.py
  checker:checker2.py => Cmd: pychecker checker2.py



Putting all together
--------------------

Really. You already learned everything you need to know! Quite easy :)

I am going to show one more real life example. Compressing javascript files, and combining them in a single file. I will use `shrinksafe <http://svn.dojotoolkit.org/branches/1.1/util/shrinksafe/custom_rhino.jar>`_.

``compressjs.py``
::

  """ dodo file - compress javascript files """

  import os

  jsPath = "./"
  jsFiles = ["file1.js", "file2.js"]

  sourceFiles = [jsPath + f for f in jsFiles]
  compressedFiles = [jsPath + "build/" + f + ".compressed" for f in jsFiles]

  def create_folder(path):
      """Create folder given by "path" if it doesnt exist"""
      if not os.path.exists(path):
	  os.mkdir(path)
      return True

  def task_create_build_folder():
      buildFolder = jsPath + "build"
      return {'action':create_folder,
	      'args': (buildFolder,)
	      }

  def task_shrink_js():
      for jsFile,compFile in zip(sourceFiles,compressedFiles):
	  action = 'java -jar custom_rhino.jar -c %s > %s'% (jsFile, compFile)
	  yield {'action':action,
		 'name':jsFile,
		 'dependencies':(":create_build_folder", jsFile,),
		 'targets':(compFile,)
		 }

  def task_pack_js():
      output = jsPath + 'compressed.js'
      input = compressedFiles
      action = "cat %s > %s"% (" ".join(input), output)
      return {'action': action,
	      'dependencies': input,
	      'targets':[output]}


Running::

  doit -f compressjs.py


Let's start from the end. 

``task_pack_js`` will combine all compressed javascript files into a single file.

``task_shrink_js`` compress a single javascript file and save the result in the "build" folder.

``task_create_build_folder`` is used to create a *build* folder to store the compressed javascript files (if the folder doesnt exist yet). Note that this task will always be execute because it doesnt have dependencies. But even it is a dependency for every "shrink_js" task it will be executed only once per `doit` run. The same task is never executed twice.

Next Steps
----------

Check the `reference <reference.html>`_ page for `doit` command line options and a summary of task dictionary fields.

There are also more `examples <examples.html>`_. Including the one used to generate this website from ReSTructured text.

Then join our `discussion forum <http://groups.google.co.in/group/python-doit>`_ and drop me a line about your experience using `doit`. I will set-up a recipes page with more examples. Contributions are welcome.

Finally take a look at the developer's `docs <developer.html>`_.


