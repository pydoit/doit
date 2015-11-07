from doit.task import clean_targets

def simple():
    print("ok")

def task_poo():
    return {
        'actions': ['touch poo'],
        'targets': ['poo'],
        'clean': [clean_targets, simple],
        }
