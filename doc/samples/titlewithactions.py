from doit.tools import title_with_actions

def task_with_details():
    return {'actions': ['echo abc 123'],
            'title': title_with_actions}
