from doit import get_var

config = {"abc": get_var('abc', 'NO')}

def task_echo():
    return {'actions': ['echo hi %s' % config],
            'verbosity': 2,
            }
