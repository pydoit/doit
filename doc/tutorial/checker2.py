import glob;

pyFiles = glob.glob('*.py')

def task_checker():
    for f in pyFiles:
        yield {'action': "pychecker %s"% f,
               'name':f,
               'dependencies':(f,)}

