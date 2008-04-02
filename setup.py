from distutils.core import setup

setup(name = 'doit',
      description = 'DoIt - A task execution tool (build-tool)',
      version = '0.1',
      license= 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'https://launchpad.net/doit',

      packages = ['doit'],
      package_dir = {'':'lib'},
      scripts = ['bin/doit'],
      
      long_description = """DoIt is a build tool that focus not only on making/building things but on executing any kind of tasks in an efficient way. Designed to be easy to use and "get out of your way"."""

      )

