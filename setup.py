#! /usr/bin/env python

from distutils.core import setup, Command


install_requires = ['six']


########### platform specific stuff #############
import platform
platform_system = platform.system()

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


long_description = """
`doit` comes from the idea of bringing the power of build-tools
to execute any kind of **task**

`website/docs <http://pydoit.org>`_
"""

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.24.0',
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
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
      long_description = long_description,
      )
