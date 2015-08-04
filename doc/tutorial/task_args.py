from __future__ import print_function

def func_with_args(arg_first, arg_second):
    print(arg_first)
    print(arg_second)
    return True
    
def task_call_func():
    return {
        'actions': [
            (func_with_args, ['This is a first argument.', 'This is a second argument.']),
            (func_with_args, ('Another first argumnt.', 'Another second argument.'))
        ]
    }
