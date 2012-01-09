#! /usr/bin/env python

from distutils.core import setup, Command

import sys
if sys.version_info >= (3,0):
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup


########### platform specific stuff #############
import platform
platform_system = platform.system()

install_requires = []
# auto command dependencies to watch file-system
if platform_system == "Darwin":
    install_requires.append('macfsevents')
elif platform_system == "Linux":
    install_requires.append('pyinotify')

scripts = ['bin/doit']
# platform specific scripts
if platform_system == "Windows":
    scripts.append('bin/doit.bat')

##################################################


if sys.version_info < (2, 6):
    install_requires.append('multiprocessing')
    install_requires.append('simplejson')


# http://pytest.org/goodpractises.html
class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys, subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


extra = {}
if sys.version_info >= (3,0):
    extra.update(use_2to3=True)


setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.15.0',
      license = 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'http://python-doit.sourceforge.net/',
      classifiers = ['Development Status :: 5 - Production/Stable',
                     'Environment :: Console',
                     'License :: OSI Approved :: MIT License',
                     'Natural Language :: English',
                     'Operating System :: OS Independent',
                     'Operating System :: POSIX',
                     'Programming Language :: Python :: 2',
                     'Programming Language :: Python :: 2.5',
                     'Programming Language :: Python :: 2.6',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3',
                     'Programming Language :: Python :: 3.2',
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
      scripts = scripts,
      cmdclass = {'test': PyTest},
      install_requires = install_requires,
      long_description = open('doc/index.rst').read().split('Quick Start')[0],
      **extra
      )

