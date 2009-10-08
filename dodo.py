"""dodo file. run pychecker and unittests."""

import glob

DEFAULT_TASKS = ['checker', 'nose']

codeFiles = glob.glob("lib/doit/*.py")
testFiles = glob.glob("tests/*.py")
pyFiles = codeFiles + testFiles

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

# TODO task should be able to control its default verbosity
# this task will run but not show results by default! need to use -v2
def task_coverage():
    """show coverage for all modules including tests"""
    return {'actions':["nosetests --with-coverage --cover-erase "
                       "--cover-package=doit,tests --cover-tests"]}

def task_coverage_code():
    """show coverage for all modules (exclude tests)"""
    return {'actions':["nosetests --with-coverage --cover-erase "
                       "--cover-package=doit"]}

def task_coverage_module():
    """show coverage for all modules (exclude tests)"""
    for test in testFiles:
        if not test.startswith('tests/test_'):
            continue
        yield {'name': test,
               'actions':["nosetests --with-coverage --cover-erase "
                          "--cover-package=doit,test --cover-tests %s" % test]}
