
DOIT_CONFIG = {'default_tasks': ['t3']}

def task_t1():
    return {'actions': ["touch task1"],
            'targets': ['task1']}

def task_t2():
    return {'actions': ["echo task2"]}

def task_t3():
    return {'actions': ["echo task3"],
            'file_dep': ['task1']}
