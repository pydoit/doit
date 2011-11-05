def task_hello():
    """hello from shell & python! """

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {'actions': ['echo Hello World!!! > %(targets)s',
                        python_hello],
            'targets': ["hello.txt"]
            }

