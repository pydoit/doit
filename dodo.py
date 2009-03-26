"""dodo file. run pychecker and unittests."""

import glob

pyFiles = glob.glob("lib/doit/*.py") + glob.glob("tests/*.py")

def task_nose():
    return {'action':"nosetests",
            'dependencies':pyFiles}

def task_checker():
    for file in pyFiles:
        yield {'action': "pychecker %s"% file, 
               'name':file, 
               'dependencies':(file,)}
