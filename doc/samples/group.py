def task_foo():
    return {'actions': ["echo foo"]}

def task_bar():
    return {'actions': ["echo bar"]}

def task_mygroup():
    return {'actions': None,
            'task_dep': ['foo', 'bar']}
