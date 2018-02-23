
def gen_many_tasks():
    yield {'basename': 't1',
           'actions': ['echo t1']}
    yield {'basename': 't2',
           'actions': ['echo t2']}

def task_all():
    yield gen_many_tasks()
