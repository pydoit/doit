import glob

from doit import create_after


@create_after(executed='early', target_regex='.*\.out')
def task_build():
    for inf in glob.glob('*.in'):
        yield {
            'name': inf,
            'actions': ['cp %(dependencies)s %(targets)s'],
            'file_dep': [inf],
            'targets': [inf[:-3] + '.out'],
            'clean': True,
        }

def task_early():
    """a task that create some files..."""
    inter_files = ('a.in', 'b.in', 'c.in')
    return {
        'actions': ['touch %(targets)s'],
        'targets': inter_files,
        'clean': True,
    }
