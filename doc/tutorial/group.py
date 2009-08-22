def task_foo():
    return {'action': "echo foo"}

def task_bar():
    return {'action': "echo bar"}

def task_mygroup():
    return {'action': None,
           'dependencies': [':foo', ':bar']}
