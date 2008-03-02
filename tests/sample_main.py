
def task_string():
    return "ls -a"

def do_nothing():
    return True

def task_python():
    return do_nothing


def task_dictionary():
    return {'action':'ls -1'}

def task_dependency():
    return {'action':do_nothing,
            'dependencies':['test_main.py']}

files = ['test_core.py','test_util.py']
def task_generator():
    for f in files:
        yield {'action': "ls -l %s"%f,
               'name': f}
               
