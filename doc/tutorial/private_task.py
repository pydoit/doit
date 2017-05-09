def task__private_get_username():
    return {
        'actions': ['echo whoami']
    }


def task_other_private_get_username():
    return {
        'actions': ['echo $USER'],
        'basename': '_other_get_username'
    }

def task_hello():
    return {
        'actions': ['echo hello']
        }
