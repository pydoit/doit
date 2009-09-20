"""dodo file. run pychecker and unittests."""

import glob

pyFiles = glob.glob("lib/doit/*.py") + glob.glob("tests/*.py")

def task_checker():
    """run pyflakes on all project files"""
    for file in pyFiles:
        yield {'actions': ["pyflakes %s"% file],
               'name':file,
               'dependencies':(file,)}

def task_nose():
    """run unit-tests"""
    return {'actions':["nosetests"],
            'dependencies':pyFiles}
