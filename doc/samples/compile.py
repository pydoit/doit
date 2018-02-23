def task_compile():
    return {'actions': ["cc -c main.c"],
            'file_dep': ["main.c", "defs.h"],
            'targets': ["main.o"]
            }
