def task_gcc():
    for fname in ['file%d.c' % index for index in range(2)]:
        yield {'name': fname,
               'actions': "gcc -c %s" % fname}

def task_gcc_doc():
    """
    Compile .c files
    """
    for fname in ['file%d.c' % index for index in range(2)]:
        yield {'name': fname,
               'actions': "gcc -c %s" % fname,
               'doc': 'Compile %s' % fname}

def task_list():
    return {'actions': 'ls',
            'doc': 'List files'}

def task_list_all():
    """
    Doc string not to be used by the task object
    """
    return {'actions': 'ls',
            'doc': 'List all files'}

def task_pwd():
    """
    Print Working Directory
    """
    return {'actions': 'pwd'}




