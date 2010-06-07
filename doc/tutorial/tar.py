def task_tar():
    return {'actions': ["tar -cf foo.tar *"],
            'task_dep':['version'],
            'targets':['foo.tar']}

def task_version():
    return {'actions': ["bzr version-info > revision.txt"]}
