def task_file2():
    yield {'basename'  : 'file2',
           'file_dep'  : ["missing.txt"],
           'targets'   : ["tmp2"],
           'actions'   : ["date > tmp2"],
    }
def task_file3():
    yield {'basename'  : 'file3',
           'file_dep'  : ["tmp2"],
           'targets'   : ["tmp3"],
           'actions'   : ["date > tmp3"],
    }

    
