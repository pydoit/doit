from doit.tools import check_timestamp_unchanged

def task_create_foo():
    return {
        'actions': ['touch foo', 'chmod 750 foo'],
        'targets': ['foo'],
        'uptodate': [True],
        }

def task_on_foo_changed():
    # will execute if foo or its metadata is modified
    return {
        'actions': ['echo foo modified'],
        'task_dep': ['create_foo'],
        'uptodate': [check_timestamp_unchanged('foo', 'ctime')],
        }
