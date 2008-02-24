from doit import CmdTask

def task_nose():
    return "nosetests"

pyFiles = ["doit/__init__.py","doit/core.py","doit/main.py","doit/util.py",
           "doit/dependency.py", "tests/test_doit.py", "tests/test_util.py",
           "tests/test_dependency.py"]

def task_checker():
    for file in pyFiles:
        #yield "pychecker %s"%file
        #yield CmdTask(["pychecker", file])
        yield CmdTask(["pychecker", file], dependencies=(file,))

def bad_seed():
    xiiiiii = 5


