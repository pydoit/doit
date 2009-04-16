def task_tar():
    return {'action': "tar -cf foo.tar *",
            'dependencies':[':version'],
            'targets':['foo.tar']}

def task_version():
    return {'action':"bzr version-info > revision.txt"}
