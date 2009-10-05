def task_hello():
    """hello from shell & python! """

    def python_hello(times, text):
        output = open("hello.txt", "a")
        output.write(times * text)
        output.close()
        return True

    msg = 3 * "hi! "
    return {'actions': ['echo %s > hello.txt' % msg,
                        (python_hello, [3, "py!\n"])]
            }
