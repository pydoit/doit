def task_deps():
    return {
        'actions': None,
        'file_dep': ['defs.h'],
    }

def task_lint():
    return {
        'actions': ['echo linting'],
        'file_dep': ['main.c'],
        'params': [{'name': 'level', 'long': 'level', 'default': 'warning'}],
    }

def task_test():
    return {
        'actions': ['echo testing'],
        'inherits': ['deps', 'lint'],
    }
