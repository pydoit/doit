def task_compile():
    return {'actions': ["cc -c main.c"],
            'dependencies': ["main.c", "defs.h"],
            'targets': ["main.o"]
            }
