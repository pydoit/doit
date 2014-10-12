def task_touch():
    return {
        'actions': ['touch foo.txt'],
        'targets': ['foo.txt'],
        # force doit to always mark the task
        # as up-to-date (unless target removed)
        'uptodate': [True],
        }
