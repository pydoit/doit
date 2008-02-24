
def task_nose():
    return "nosetests"

pyFiles = ["doit.py","tests/test_doit.py"]
def task_checker():
    for file in pyFiles:
        yield "pychecker %s"%file

def bad_seed():
    xiiiiii = 5

