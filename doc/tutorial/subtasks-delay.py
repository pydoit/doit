def task_create_file():
    for i in range(6):
        filename = "file%d.txt" % i
        yield {'name': filename,
               'delay': 2,
               'actions': ['echo "task {} started (H:M:S+`date +%%S`)"'
                           .format(filename)]}
