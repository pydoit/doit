### task setup env. good for functional tests!
DOIT_CONFIG = {'verbosity': 2,
               'default_tasks': ['withenvX', 'withenvY']}

def start(name):
    print "start %s" % name
def stop(name):
    print "stop %s" % name

def task_setup_sample():
    for name in ('setupX', 'setupY'):
        yield {'name': name,
               'actions': [(start, (name,))],
               'teardown': [(stop, (name,))],
               }

def task_withenvX():
    for fin in ('a','b','c'):
        yield {'name': fin,
               'actions':['echo x %s' % fin],
               'setup': ['setup_sample:setupX'],
               }

def task_withenvY():
    return {'actions':['echo y'],
            'setup': ['setup_sample:setupY'],
            }
