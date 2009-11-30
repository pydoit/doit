
def show_cmd(task):
    return "executing... %s" % str(task)

def task_custom_display():
    return {'actions':['echo abc efg'],
            'title': show_cmd}
