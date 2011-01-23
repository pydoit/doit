def task_get_pylogo():
    url = "http://python.org/images/python-logo.gif"
    return {'actions': ["wget %s" % url],
            'targets': ["python-logo.gif"],
            'run_once': True,
            }
