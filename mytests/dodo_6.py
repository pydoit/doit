def task_file2():
    yield {'basename'  : 'file2',
           'file_dep'  : [],
           'targets'   : ["tmp2"],
           'actions'   : ["date > tmp2"],
    }
def task_file3():
    yield {'basename'  : 'file3',
           'file_dep'  : ["tmp2"],
           'targets'   : ["tmp3"],
           'actions'   : ["date > tmp3"],
    }
def task_file4():
    yield {'basename'  : 'file4',
           'file_dep'  : ["tmp3"],
           'targets'   : ["tmp4"],
           'actions'   : ["date > tmp4"],
    }
def task_file5():
    yield {'basename'  : 'file5',
           'file_dep'  : ["tmp4"],
           'targets'   : ["tmp5"],
           'actions'   : ["date > tmp5"],
    }
