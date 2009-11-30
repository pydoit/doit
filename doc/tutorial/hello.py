def task_hello():
    """hello from shell & python! """

    def python_hello(targets):
        output = open(targets[0], "a")
        output.write("Python says Hello World!!!\n")
        output.close()

    return {'actions': ['echo Hello World!!! > %(targets)s',
                        (python_hello,)],
            'targets': ["hello.txt"]
            }

