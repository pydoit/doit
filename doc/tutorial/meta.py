def who(task):
    print('my name is', task.name)
    print(task.targets)

def task_x():
    return {
        'actions': [who],
        'targets': ['asdf'],
        'verbosity': 2,
        }
