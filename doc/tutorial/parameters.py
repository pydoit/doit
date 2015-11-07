def task_py_params():
    def show_params(param1, param2):
        print(param1)
        print(5 + param2)
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

def task_py_params_list():
    def print_a_list(list):
        for item in list:
            print(item)
    return {'actions':[(print_a_list,)],
            'params':[{'name':'list',
                       'short':'l',
                       'long': 'list',
                       'type': list,
                       'default': [],
                       'help': 'Collect a list with multiple -l flags'}],
            'verbosity':2,
            }

def task_py_params_choice():
    def print_choice(choice):
        print(choice)

    return {'actions':[(print_choice,)],
            'params':[{'name':'choice',
                       'short':'c',
                       'long': 'choice',
                       'type': str,
                       'choices': (('this', ''), ('that', '')),
                       'default': 'this',
                       'help': 'Choose between this and that'}],
            'verbosity':2,}

def task_cmd_params():
    return {'actions':["echo mycmd %(flag)s xxx"],
            'params':[{'name':'flag',
                       'short':'f',
                       'long': 'flag',
                       'default': '',
                       'help': 'helpful message about this flag'}],
            'verbosity': 2
            }

