from doit.action import CmdAction

def task_hello():
    """hello cmd """

    def create_cmd_string():
        return "echo hi"

    return {
        'actions': [CmdAction(create_cmd_string)],
        'verbosity': 2,
        }
