#! /usr/bin/env python

from distutils.core import setup

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.9.x',
      license = 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'http://python-doit.sourceforge.net/',
      classifiers = ['Development Status :: 4 - Beta',
                     'Environment :: Console',
                     'Intended Audience :: Developers',
                     'Intended Audience :: System Administrators',
                     'License :: OSI Approved :: MIT License',
                     'Natural Language :: English',
                     'Operating System :: OS Independent',
                     'Operating System :: POSIX',
                     'Programming Language :: Python :: 2.4',
                     'Programming Language :: Python :: 2.5',
                     'Programming Language :: Python :: 2.6',
                     'Topic :: Software Development :: Build Tools',
                     'Topic :: Software Development :: Testing',
                     'Topic :: Software Development :: Quality Assurance',
                     ],

      packages = ['doit'],
      scripts = ['bin/doit'],
      #pyinotify
      install_requires = ['multiprocessing'],

      long_description = """
`doit` comes from the idea of bringing the power of build-tools to execute any kind of task. It will keep track of dependencies between "tasks" and execute them only when necessary. It was designed to be easy to use and "get out of your way".

Features:

 * Easy to use, "no-API"
 * Use python to dynamically create tasks on-the-fly
 * Flexible, adapts to many workflows for creation of tasks/rules/recipes
 * Support for multi-process parallel execution
 * Built-in integration of inotify (automatically re-execution)

`doit` can be used as:

 * a build tool (generic and flexible)

 * home of your management scripts (it helps you organize and combine shell scripts and python scripts)

 * a functional tests runner (combine together different tools)


In `doit`, unlike most (all?) build-tools, a task doesn't need to define a target file to use the execute only if not up-to-date feature. This make `doit` specially suitable for running a sub-set of your test suites.

`doit` like most build tools is used to execute tasks defined in a configuration file. Configuration files are python modules. The tasks can be python functions or an external shell script/command. `doit` automatically keeps track of declared dependencies executing only tasks that needs to be updated

If you are still wondering why someone would want to use this tool, check this blog `post <http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale/>`_.
"""
      )

