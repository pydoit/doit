"""dodo file. run pychecker and unittests."""

import glob

DOIT_CONFIG = {'default_tasks': ['checker', 'ut']}

codeFiles = glob.glob("doit/*.py")
testFiles = glob.glob("tests/test_*.py")
pyFiles = codeFiles + testFiles

def task_checker():
    """run pyflakes on all project files"""
    for file in pyFiles:
        yield {'actions': ["pyflakes %s"% file],
               'name':file,
               'file_dep':(file,),
               'title': (lambda task: task.name)}

def task_ut():
    """run unit-tests"""
    for test in testFiles:
        yield {'name': test,
               'actions': ["py.test %s" % test],
               'file_dep': pyFiles,
               'verbosity': 0}




def task_coverage():
    """show coverage for all modules including tests"""
    return {'actions':
                ["coverage run --parallel-mode `which py.test` ",
                 "coverage combine",
                 "coverage report --show-missing %s" % " ".join(pyFiles)],
            'verbosity': 2}

def task_coverage_code():
    """show coverage for all modules (exclude tests)"""
    return {'actions':
                ["coverage run --parallel-mode `which py.test` ",
                 "coverage combine",
                 "coverage report --show-missing %s" % " ".join(codeFiles)],
            'verbosity': 2}

def task_coverage_module():
    """show coverage for individual modules"""
    to_strip = len('tests/test_')
    for test in testFiles:
        if not test.startswith('tests/test_'):
            continue
        source = "doit/" + test[to_strip:]
        yield {'name': test,
               'actions':
                   ["coverage run --parallel-mode `which py.test` -v %s" % test,
                    "coverage combine",
                    "coverage report --show-missing %s %s" % (source, test)],
               'verbosity': 2}


# distribute => setup.py test together with use_2to3 doesnt work hence this
def task_test3():
    """run unitests on python3"""
    import os
    this_folder = os.path.dirname(os.path.abspath(__file__))
    test_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "../doit3test")
    return {'actions': [
            "rm -rf %s" % test_folder,
            "cp -r %s %s" % (this_folder, test_folder),
            "2to3 --write --nobackups %s" % test_folder,
            "py.test-3.2 -x %s" % test_folder,
            ],
            'verbosity': 2,
            }


# sfood -i doit/ | sfood-graph | dot -Tpng -o doit-dep.png
