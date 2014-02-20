# import task_ functions
from get_var import task_echo

# import tasks with create_doit_tasks callable
from custom_task_def import sample


def task_hello():
    return {'actions': ['echo hello']}

