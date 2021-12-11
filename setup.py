#! /usr/bin/env python3

from __future__ import print_function
import sys

from setuptools import setup


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
      version = '0.34.0',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
      keywords = "build make task automation pipeline",
      project_urls = {
          'Documentation': 'https://pydoit.org/',
          'Source': 'https://github.com/pydoit/doit/',
          'Tracker': 'https://github.com/pydoit/doit/issues',
      },
      packages = ['doit'],
      python_requires='>=3.6',
      install_requires = ['cloudpickle'],
      extras_require={
          ':sys.platform == "darwin"': ['macfsevents'],
          ':sys.platform == "linux"': ['pyinotify'],
          'plugins': ['setuptools'],
          'toml': ['toml >=0.10.1']
      },
      long_description = long_description,
      entry_points = {
          'console_scripts': [
              'doit = doit.__main__:main'
          ]
      },
      )
