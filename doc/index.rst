:orphan:

.. rubric::
    `doit` is a task management & automation tool

.. rubric::
    `doit` comes from the idea of bringing the power of build-tools
    to execute any kind of **task**

`doit` is a modern open-source build-tool written in python
designed to be simple to use and flexible to deal with complex work-flows.
It is specially suitable for building and managing custom work-flows where
there is no out-of-the-box solution available.

`doit` has been successfully used on: systems test/integration automation,
scientific computational pipelines, content generation,
configuration management, etc.
Check some `success stories <stories.html>`_ ...



introduction
============

A **task** describes some computation to be done (*actions*),
and contains some extra meta-data.

.. code-block:: python

  def task_example():
      return {
          'actions': ['myscript'],
          'file_dep': ['my_input_file'],
          'targets': ['result_file'],
      }


**actions**:

- can be external programs (executed as shell commands) or
  python functions.
- a single task may define more than one action.


**task meta-data**:

- task meta-data includes a description of input file (**dependencies**)
  for the *actions* and result files (**targets**)
- there are many other meta-data fields to control how and when a task is
  executed...

*doit* uses the task's meta-data to:

.. topic:: cache task results (aka *incremental-builds*)

   `doit` checks if the task is **up-to-date** and skips its execution if the
   task would produce the same result of a previous execution.

.. topic:: correct execution order

   By checking the inter-dependency between tasks `doit` ensures that tasks
   will be execute in the correct order.

.. topic:: parallel execution

   built-in support for parallel (threaded or multi-process) task execution
   (:ref:`more <parallel-execution>`)


Traditional build-tools were created mainly to deal with compile/link
process of source code. `doit` was designed to solve a broader range of tasks.

.. topic:: powerful dependency system

   - the *up-to-date* check is not restricted to looking for
     file modification on dependencies,
     it can be customized for each task (:ref:`more <attr-uptodate>`)
   - *target* files are not required in order to check if a task is up-to-date
     (:ref:`more <up-to-date-def>`)
   - *dependencies* can be dynamically calculated by other tasks
     (:ref:`more <attr-calc_dep>`)


Task's metadata (actions, dependencies, targets...) are better described
in a declarative way,
but often you want to create this metadata programmatically.

.. topic:: flexible task definition

   `doit` uses plain python modules to create tasks (and its meta-data)


.. topic:: customizable task definition

   By default tasks are described by a python `dict`.
   But it can be easily customized. (:ref:`more <create-doit-tasks>`)


.. topic:: debugger

   Since plain python is used to define your tasks the python debugger (`pdb`)
   is available as in any other python application


Other features...

.. topic:: self documented

  `doit` command allows you to list and obtain help/documentation for tasks
  (:ref:`more <cmd-list>`)

.. topic:: inotify integration

  built-in support for a long-running process that automatically re-execute tasks
  based on file changes by external process (linux/mac only)
  (:ref:`more <cmd-auto>`)

.. topic:: custom output

  process output can be completely customized through *reporters*
  (:ref:`more <reporter>`)

.. topic:: tab-completion

  built-in support tab-completion for commands/task (supports bash and zsh)
  (:ref:`more <tabcompletion>`)

.. topic:: IPython integration

  provide `%doit` magic function that loads tasks defined directly in IPython's
  global namespace
  (:ref:`more <tools.IPython>`)

.. topic:: extensible

  Apart from using `doit` to automate your project it also expose its API
  so you can create new applications/tools using `doit` functionality
  (:ref:`more <extending>`)

Check the `documentation <contents.html>`_ for more features...


What people are saying about `doit`
=====================================

  Congratulations! **Your tool follows the KISS principle very closely**. I always wondered why build tools had to be that complicated. - `Elena <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/#comment-514>`_

  Let me start by saying I'm really lovin doit, at first the interface seemed verbose but quickly changed my mind when **I started using it and realized the flexibility**.  Many thanks for the great software! - `Michael Gliwinski <https://groups.google.com/d/msg/python-doit/7cD2RiBhB9c/FzrAWkVhEgUJ>`_

  I love all the traditional unix power tools, like cron, make, perl, ..., I also like new comprehensive configuration management tools like CFEngine and Puppet.  But **I find doit to be so versatile and so productive**. - `Charlie Guo <https://groups.google.com/d/msg/python-doit/JXElpPfcmmM/znvBT0OFhMYJ>`_

  I went back and forth on different Pythonic build tools for awhile. Scons is pretty great if you're doing 'standard' sorts of builds, but I found it a little heavy for my tastes and really hard to customize to my tool flow (in FPGA land, there are all kinds of nonstandard vendor tools that all need to play together). I've been using doit more and more over the past few months, and I'm continually impressed by the tool (aside from the goofy name). **It works amazingly well for automating tricky/exotic build processes**. Check it out! `SkOink <http://news.slashdot.org/comments.pl?sid=4319575&cid=45085519>`_

  I needed a sort of 'make' tool to glue things together and after trying out all kinds, **doit ... has actually turned out to be beautiful**. Its easy to add and manage tasks, even complex ones-- gluing things together with decorators and 'library' functions I've written to do certain similar things. - `Matthew <https://groups.google.com/d/msg/python-doit/eKI0uu02ZeY/cBU0RRsO0_cJ>`_

  Some time ago, I grew frustrated with Make and Ant and started porting my build files to every build tool I found (SCons, Waf, etc.). Each time, as soon as I stepped out of already available rules, I ran into some difficult to overcome stumbling blocks. **Then I discovered this little gem of simplicity: doit**. It's Python-based. It doesn't try to be smart, it does not try to be cool, it just works. If you are looking for a flexible little build tool for different languages and tasks, give it a chance. (...) - `lelele <http://www.hnsearch.com/search#request/all&q=python-doit.sourceforge.net&start=0>`_


`Success Stories... <stories.html>`_

Project Details
===============

* **LICENSE** This is an open-source project
  (`MIT license <http://opensource.org/licenses/mit-license.php>`_)
  written in python. Runs on Python 3.4 through 3.6 (including PyPy support). For python 2 support please use *doit* version 0.29.

* **DOWNLOAD** from `PyPi <http://pypi.python.org/pypi/doit>`_

* **CONTRIBUTE** Please check the community `guidelines <https://github.com/pydoit/doit/blob/master/CONTRIBUTING.md>`_ before asking questions and reporting issues.

* **DEVELOP** Project management (bug tracker, feature requests and source code ) on `github <https://github.com/pydoit/doit>`_.

* **QUESTIONS** on `StackOverflow <https://stackoverflow.com/questions/tagged/doit>`_, use tag `doit`.

* **FORUM** (questions/feedback/discussion) on `Google group <http://groups.google.co.in/group/python-doit>`_. Please do **not** send questions to my private email.

* `doit projects <https://github.com/pydoit/doit/wiki/powered-by-doit>`_ contains a collection of third-party projects, plugins, extensions, non-trivial examples and re-usable task creators for `doit`.

* This web site is hosted on http://pages.github.com

* Professional support and consulting services available from `doit`
  creator & maintainer (*schettino72* at gmail.com).



Status
======

This blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_ explains how everything started in 2008.

`doit` is under active development. Version 0.31 released on 2018-02.

`doit` core features are quite stable. If there is no recent development,
it does NOT mean `doit` is not being maintained...
The project has 100% unit-test code coverage.

Development is done based on real world use cases.
It is well designed and has a small code base,
so adding new features is not hard. Contributions are welcome.
