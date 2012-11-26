def task_hello():
    """hello from shell & python! """

    def python_hello(times, text):
        with open("hello.txt", "a") as output:
            output.write(times * text)

    msg = 3 * "hi! "
    return {'actions': ['echo %s ' % msg + ' > %(targets)s',
                        (python_hello, [3, "py!\n"])],
            'targets': ["hello.txt"],
            }
