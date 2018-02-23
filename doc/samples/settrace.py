
def need_to_debug():
    # some code here
    from doit import tools
    tools.set_trace()
    # more code

def task_X():
    return {'actions':[(need_to_debug,)]}
