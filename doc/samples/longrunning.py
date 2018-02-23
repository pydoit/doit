from doit.tools import LongRunning

def task_top():
    cmd = "top"
    return {'actions': [LongRunning(cmd)],}
