def task_file2():
    yield {'basename'  : 'file2',
           'file_dep'  : ["missing.txt"],
           'targets'   : ["tmp2"],
           'actions'   : ["date > tmp2"],
       }
