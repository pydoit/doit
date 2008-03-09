
def task_nose():
    return "nosetests"

pyFiles = ["doit/__init__.py","doit/core.py","doit/task.py","doit/main.py",
           "doit/util.py",  "doit/dependency.py", "doit/loader.py", 
           "tests/__init__.py", "tests/test_core.py", "tests/test_task.py",
           "tests/test_util.py", "tests/test_dependency.py",
           "tests/test_loader.py", "tests/test_main.py"]

def task_checker():
    for file in pyFiles:
        yield {'action': ["pychecker",file], 
               'name':file, 
               'dependencies':(file,)}

def bad_seed():
    xiiiiii = 5


