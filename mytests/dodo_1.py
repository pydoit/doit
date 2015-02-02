def task_hello():
    """hello"""

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {
        'file_dep': ["existing.txt"],
        'actions': [python_hello],
        'targets': ["output1.txt"],
        'clean': True,
    }
