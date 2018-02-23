import glob

def task_xxx():
    """my doc"""
    LIST = glob.glob('*.xyz') # might be empty
    yield {
        'basename': 'do_x',
        'name': None,
        'doc': 'docs for X',
        'watch': ['.'],
        }
    for item in LIST:
        yield {
            'basename': 'do_x',
            'name': item,
            'actions': ['echo %s' % item],
            'verbosity': 2,
            }
