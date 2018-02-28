from doit.tools import Background

def task_sleep():
    cmd = 'sleep 10; echo "after 10 seconds"'
    return {'actions': [Background(cmd)],}
