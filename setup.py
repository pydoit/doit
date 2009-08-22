
from distutils.core import setup

setup(name = 'doit',
      description = 'doit - Automation Tool',
      version = '0.2.0',
      license= 'MIT',
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
      package_dir = {'':'lib'},
      scripts = ['bin/doit'],

      long_description = """
        doit comes from the idea of bringing the power of build-tools to 
        execute any kind of task. It will keep track of dependencies between 
        "tasks" and execute them only when necessary. It was designed to be 
        easy to use and "get out of your way"."""
      )

