import datetime
from doit.tools import timeout

def task_expire():
    return {
            'actions': ['echo test expire; date'],
            'uptodate': [timeout(datetime.timedelta(minutes=5))],
            'verbosity': 2,
           }
