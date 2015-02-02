def task_chain_phony():
    yield {'name': 't1',
           'targets'   : ["tmp1_phony"],
           'actions'   : ["echo hi1 > tmp1_phony"],
       }
    yield {'name': 't2',
           'file_dep'  : ["tmp1_phony"],
           'targets'   : ["tmp2_phony"],
           'actions'   : ["echo hi2 > tmp2_phony"],
       }
