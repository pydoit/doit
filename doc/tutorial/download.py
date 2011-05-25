from doit.tools import run_once

def task_get_pylogo():
    url = "http://python.org/images/python-logo.gif"
    return {'actions': ["wget %s" % url],
            'targets': ["python-logo.gif"],
            'uptodate': [run_once],
            }
