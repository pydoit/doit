"""dodo file. run pychecker and unittests."""

import glob

pyFiles = glob.glob("lib/doit/*.py") + glob.glob("tests/*.py")

def task_checker():
    for file in pyFiles:
        yield {'actions': "pyflakes %s"% file,
               'name':file,
               'dependencies':(file,)}

def task_nose():
    return {'actions':"nosetests",
            'dependencies':pyFiles}
