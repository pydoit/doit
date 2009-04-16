from distutils.core import setup

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.1.0',
      license= 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'http://python-doit.sourceforge.net/',
      classifiers = ['Development Status :: 3 - Alpha',
                     'Environment :: Console',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved :: MIT License',
                     'Natural Language :: English',
                     'Operating System :: POSIX',
                     'Topic :: Software Development :: Build Tools',
                     'Topic :: Software Development :: Quality Assurance',
                     FIXME
                     ],

      packages = ['doit'],
      package_dir = {'':'lib'},
      scripts = ['bin/doit'],
      
      long_description = FIXME"""
        doit is a build tool that focus not only on making/building things but 
        on executing any kind of tasks in an efficient way. Designed to be easy
        to use and "get out of your way"."""
      )

