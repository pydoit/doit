
def task_count_lines():
    return {'action': "wc -l files.txt > count.txt",
            'dependencies':[':ls'],
            'targets':['count.txt']}

def task_ls():
    return {'action':"ls -1 > files.txt",
            'targets':['files.txt']}

