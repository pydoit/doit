def task_hello():
    """say hello"""
    return {
        'actions': ['echo hello']
        }

def task_xxx():
    """say hello again"""
    return {
        'basename': 'hello2',
        'actions': ['echo hello2']
        }
