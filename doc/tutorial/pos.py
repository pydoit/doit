def task_pos_args():
    def show_params(param1, pos):
        print('param1 is: {0}'.format(param1))
        for index, pos_arg in enumerate(pos):
            print('positional-{0}: {1}'.format(index, pos_arg))
    return {'actions':[(show_params,)],
            'params':[{'name':'param1',
                       'short':'p',
                       'default':'default value'},
                      ],
            'pos_arg': 'pos',
            'verbosity': 2,
            }
