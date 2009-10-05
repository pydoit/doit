def task_tar():
    return {'actions': ["tar -cf foo.tar *"],
            'dependencies':[':version'],
            'targets':['foo.tar']}

def task_version():
    return {'actions': ["bzr version-info > revision.txt"]}
