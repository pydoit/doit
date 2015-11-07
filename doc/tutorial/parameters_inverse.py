def task_with_flag():
    def _task(flag):
        print("Flag {0}".format("On" if flag else "Off"))

    return {
        'params': [{
            'name': 'flag',
            'long': 'flagon',
            'short': 'f',
            'type': bool,
            'default': True,
            'inverse': 'flagoff'}],
        'actions': [(_task, )],
        'verbosity': 2
        }
