def make_task(func):
    """make decorated function a task-creator"""
    func.create_doit_tasks = func
    return func

@make_task
def sample():
    return {
        'verbosity': 2,
        'actions': ['echo hi'],
        }
