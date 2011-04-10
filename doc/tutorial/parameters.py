def task_py_params():
    def show_params(param1, param2):
        print param1
        print 5 + param2
    return {'actions':[(show_params,)],
            'params':[{'name':'param1',
                       'short':'p',
                       'default':'default value'},

                      {'name':'param2',
                       'long':'param2',
                       'type': int,
                       'default':0}],
            'verbosity':2,
            }

def task_cmd_params():
    return {'actions':["echo mycmd %(flag)s xxx"],
            'params':[{'name':'flag',
                       'short':'f',
                       'long': 'flag',
                       'default': ''}],
            'verbosity': 2
            }

