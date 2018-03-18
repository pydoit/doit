def my_cleaner(dryrun):
    if dryrun:
        print('dryrun, dont really execute')
        return
    print('execute cleaner...')

def task_sample():
    return {
        "actions" : None,
        "clean"   : [my_cleaner],
    }

