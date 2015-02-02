def task_with_task_dep():
    yield {'name': 't1',
           'actions': ["echo hi1"],
           'file_dep': ['modified.txt'],
       }
    yield {'name': 't2',
           'actions': ["echo hi2"],
           'uptodate': [lambda: True],
           'task_dep': ['with_task_dep:t1'],
       }
