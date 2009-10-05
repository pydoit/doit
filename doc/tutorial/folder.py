from doit.tools import create_folder

BUILD_PATH = "_build"

def task_build():
    return {'actions': [(create_folder, [BUILD_PATH]),
                        'touch %(targets)s'],
            'targets': ["%s/file.o" % BUILD_PATH]
            }
