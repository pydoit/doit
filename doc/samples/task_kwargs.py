def func_with_args(arg_first, arg_second):
    print(arg_first)
    print(arg_second)
    return True

def task_call_func():
    return {
        'actions': [(func_with_args, [], {
            'arg_second': 'This is a second argument.',
            'arg_first': 'This is a first argument.'})
        ],
        'verbosity': 2,
    }
