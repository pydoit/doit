#! /usr/bin/env python3

def task_echo():
    return {
        'actions': ['echo hi'],
        'verbosity': 2,
        }

if __name__ == '__main__':
    import doit
    doit.run(globals())
