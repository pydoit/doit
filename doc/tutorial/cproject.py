DOIT_CONFIG = {'default_tasks': ['link']}

# map source file to dependencies
SOURCE = {
    'main': ["defs.h"],
    'kbd': ["defs.h", "command.h"],
    'command': ["defs.h", "command.h"],
    }

def task_link():
    "create binary program"
    OBJECTS = ["%s.o" % module for module in SOURCE.iterkeys()]
    return {'actions': ['cc -o %(targets)s %(dependencies)s'],
            'dependencies': OBJECTS,
            'targets': ['edit'],
            'clean': True
            }

def task_compile():
    "compile C files"
    for module, dep in SOURCE.iteritems():
        dependencies = dep + ['%s.c' % module]
        yield {'name': module,
               'actions': ["cc -c %s.c" % module],
               'targets': ["%s.o" % module],
               'dependencies': dependencies,
               'clean': True
               }

def task_install():
    "install"
    return {'actions': ['echo install comes here...'],
            'dependencies': [':link'],
            'doc': 'install executable (TODO)'
            }
