def task_chain():
    yield {'name': 't1',
           'targets'   : ["tmp1"],
           'actions'   : ["echo hi1 > tmp1"],
           'uptodate': [True],
       }
    yield {'name': 't2',
           'file_dep'  : ["tmp1"],
           'targets'   : ["tmp2"],
           'actions'   : ["echo hi2 > tmp2"],
       }
