
def show_cmd(task):
    return "executing... %s" % task.name

def task_custom_display():
    return {'actions':['echo abc efg'],
            'title': show_cmd}
