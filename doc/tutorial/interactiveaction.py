from doit.tools import InteractiveAction

def task_top():
    cmd = "top"
    return {'actions': [InteractiveAction(cmd)],}
