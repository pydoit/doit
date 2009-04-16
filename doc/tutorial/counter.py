
def task_count_lines():
    return {'action': "wc -l build/files.txt > result/count.txt",
            'dependencies':['result/', 'build/files.txt'],
            'targets':['result/count.txt']}

def task_ls():
    return {'action':"ls -1 > build/files.txt",
            'dependencies':['build/'],
            'targets':['build/files.txt']}

