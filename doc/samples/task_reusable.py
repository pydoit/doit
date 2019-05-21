
def gen_many_tasks():
    """ first line of docstring becomes doc kwarg """
    yield {'basename': 't1',
           'actions': ['echo t1']}
    yield {'basename': 't2',
           'actions': ['echo t2'],
           'doc': "t2 override of doc kwarg"}

def task_all():
    yield gen_many_tasks()
