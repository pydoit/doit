from doit.action import CmdAction

def task_save_output():
    return {
        'actions': [CmdAction("echo x1", save_out='out')],
        }
# The task values will contain: {'out': u'x1'}
