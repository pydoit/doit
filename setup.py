#! /usr/bin/env python

import sys

from setuptools import setup


install_requires = ['six']


########### platform specific stuff #############
import platform
platform_system = platform.system()

# auto command dependencies to watch file-system
if platform_system == "Darwin":
    install_requires.append('macfsevents')
elif platform_system == "Linux":
    install_requires.append('pyinotify')

##################################################

if sys.version_info < (3, 0):
    install_requires.append('configparser')



long_description = """
`doit` comes from the idea of bringing the power of build-tools
to execute any kind of **task**

`website/docs <http://pydoit.org>`_
"""

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.28.dev0',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Scientific/Engineering',
        ],

      packages = ['doit'],
      install_requires = install_requires,
      long_description = long_description,
      entry_points = {
          'console_scripts': [
              'doit = doit.__main__:main'
          ]
      },
      )
