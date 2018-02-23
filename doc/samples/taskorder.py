def task_modify():
    return {'actions': ["echo bar > foo.txt"],
            'file_dep': ["foo.txt"],
            }

def task_create():
    return {'actions': ["touch foo.txt"],
            'targets': ["foo.txt"]
            }
