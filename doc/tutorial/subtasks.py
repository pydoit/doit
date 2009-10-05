def task_create_file():
    for i in range(3):
        filename = "file%d.txt" % i
        yield {'name': filename,
               'actions': ["touch %s" % filename]}
