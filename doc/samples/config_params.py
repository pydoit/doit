from doit.tools import config_changed

option = "AB"
def task_with_params():
    return {'actions': ['echo %s' % option],
            'uptodate': [config_changed(option)],
            'verbosity': 2,
            }
