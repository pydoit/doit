def task_hello():
    """hello from shell & python! """

    def python_hello():
        output = open("hello.txt", "a")
        output.write("Python says Hello World!!!\n")
        output.close()

    return {'actions': ['echo Hello World!!! > hello.txt',
                        (python_hello,)]
            }

