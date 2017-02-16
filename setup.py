#! /usr/bin/env python

import sys

from setuptools import setup


install_requires = ['cloudpickle']


########### last version to support python2 is 0.29 ####
if sys.version_info[0] < 3:
    sys.exit('This version of doit is only supported by Python 3.\n' +
             'Please use doit==0.29.0 with Python 2.')

########################################################

long_description = """
`doit` is a task management & automation tool

`doit` comes from the idea of bringing the power of build-tools
to execute any kind of **task**

`doit` is a modern open-source build-tool written in python
designed to be simple to use and flexible to deal with complex work-flows.
It is specially suitable for building and managing custom work-flows where
there is no out-of-the-box solution available.

`doit` has been successfully used on: systems test/integration automation,
scientific computational pipelines, content generation,
configuration management, etc.

`website/docs <http://pydoit.org>`_
"""

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.30.0',
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
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Scientific/Engineering',
        ],
      keywords = "build make task automation pipeline",

      packages = ['doit'],
      install_requires = install_requires,
      extras_require={
          ':python_version <= "3.3"': ['pathlib2'],
          ':sys.platform == "darwin"': ['macfsevents'],
          ':sys.platform == "linux"': ['pyinotify'],
      },
      long_description = long_description,
      entry_points = {
          'console_scripts': [
              'doit = doit.__main__:main'
          ]
      },
      )
