#! /usr/bin/env python3

import sys

from setuptools import setup


long_description = '''
*doit* comes from the idea of bringing the power of build-tools to execute any
kind of task

*doit* can be uses as a simple **Task Runner** allowing you to easily define ad hoc
tasks, helping you to organize all your project related tasks in an unified
easy-to-use & discoverable way.

*doit* scales-up with an efficient execution model like a **build-tool**.
*doit* creates a DAG (direct acyclic graph) and is able to cache task results.
It ensures that only required tasks will be executed and in the correct order
(aka incremental-builds).

The *up-to-date* check to cache task results is not restricted to looking for
file modification on dependencies.  Nor it requires "target" files.
So it is also suitable to handle **workflows** not handled by traditional build-tools.

Tasks' dependencies and creation can be done dynamically during it is execution
making it suitable to drive complex workflows and **pipelines**.

*doit* is build with a plugin architecture allowing extensible commands, custom
output, storage backend and "task loader". It also provides an API allowing
users to create new applications/tools leveraging *doit* functionality like a framework.

*doit* is a mature project being actively developed for more than 10 years.
It includes several extras like: parallel execution, auto execution (watch for file
changes), shell tab-completion, DAG visualisation, IPython integration, and more.



Sample Code
===========

Define functions returning python dict with task's meta-data.

Snippet from `tutorial <http://pydoit.org/tutorial-1.html>`_:

.. code:: python

  def task_imports():
      """find imports from a python module"""
      for name, module in PKG_MODULES.by_name.items():
          yield {
              'name': name,
              'file_dep': [module.path],
              'actions': [(get_imports, (PKG_MODULES, module.path))],
          }

  def task_dot():
      """generate a graphviz's dot graph from module imports"""
      return {
          'targets': ['requests.dot'],
          'actions': [module_to_dot],
          'getargs': {'imports': ('imports', 'modules')},
          'clean': True,
      }

  def task_draw():
      """generate image from a dot file"""
      return {
          'file_dep': ['requests.dot'],
          'targets': ['requests.png'],
          'actions': ['dot -Tpng %(dependencies)s -o %(targets)s'],
          'clean': True,
      }


Run from terminal::

  $ doit list
  dot       generate a graphviz's dot graph from module imports
  draw      generate image from a dot file
  imports   find imports from a python module
  $ doit
  .  imports:requests.models
  .  imports:requests.__init__
  .  imports:requests.help
  (...)
  .  dot
  .  draw


Project Details
===============

 - Website & docs - `http://pydoit.org <http://pydoit.org>`_
 - Project management on github - `https://github.com/pydoit/doit <https://github.com/pydoit/doit>`_
 - Discussion group - `https://groups.google.com/forum/#!forum/python-doit <https://groups.google.com/forum/#!forum/python-doit>`_
 - News/twitter - `https://twitter.com/pydoit <https://twitter.com/pydoit>`_
 - Plugins, extensions and projects based on doit - `https://github.com/pydoit/doit/wiki/powered-by-doit <https://github.com/pydoit/doit/wiki/powered-by-doit>`_

license
=======

The MIT License
Copyright (c) 2008-2022 Eduardo Naufel Schettino
'''

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.36.0',
      license = 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'http://pydoit.org',
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Scientific/Engineering',
        ],
      keywords = "build make task automation pipeline task-runner",
      project_urls = {
          'Documentation': 'https://pydoit.org/',
          'Source': 'https://github.com/pydoit/doit/',
          'Tracker': 'https://github.com/pydoit/doit/issues',
      },
      packages = ['doit'],
      python_requires='>=3.8',
      install_requires = ['cloudpickle', 'importlib-metadata>=4.4'],
      extras_require={
          'toml': ['tomli; python_version<"3.11"']
      },
      long_description = long_description,
      entry_points = {
          'console_scripts': [
              'doit = doit.__main__:main'
          ]
      },
      )
