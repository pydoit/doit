"""dodo file. test + management stuff"""

import glob
import os
import subprocess

import pytest

from doit.tools import create_folder

DOIT_CONFIG = {
    'minversion': '0.24.dev0',
    'default_tasks': ['checker', 'ut'],
#    'backend': 'sqlite3',
    }

CODE_FILES = glob.glob("doit/*.py")
TEST_FILES = glob.glob("tests/test_*.py")
TESTING_FILES = glob.glob("tests/*.py")
PY_FILES = CODE_FILES + TESTING_FILES


def task_checker():
    """run pyflakes on all project files"""

    def add_pyflakes_builtins():
        os.environ['PYFLAKES_BUILTINS'] = 'unicode'
    yield {
        'basename': '_pyflakes_builtins',
        'actions': [add_pyflakes_builtins]
        }

    for module in PY_FILES:
        yield {'actions': ["pyflakes %(dependencies)s"],
               'name':module,
               'file_dep':(module,),
               'setup':['_pyflakes_builtins'],
               'title': (lambda task: task.name)}

def run_test(test):
    return not bool(pytest.main(test))
    #return not bool(pytest.main("-v " + test))
def task_ut():
    """run unit-tests"""
    for test in TEST_FILES:
        yield {'name': test,
               'actions': [(run_test, (test,))],
               'file_dep': PY_FILES,
               'verbosity': 0}


################## coverage tasks

def task_coverage():
    """show coverage for all modules including tests"""
    return {'actions':
                ["coverage run --parallel-mode `which py.test` ",
                 "coverage combine",
                 ("coverage report --show-missing %s" %
                  " ".join(CODE_FILES + TEST_FILES))
                 ],
            'verbosity': 2}


def task_coverage_code():
    """show coverage for all modules (exclude tests)"""
    return {'actions':
                ["coverage run --parallel-mode `which py.test` ",
                 "coverage combine",
                 "coverage report --show-missing %s" % " ".join(CODE_FILES)],
            'verbosity': 2}


def task_coverage_module():
    """show coverage for individual modules"""
    to_strip = len('tests/test_')
    for test in TEST_FILES:
        source = "doit/" + test[to_strip:]
        yield {'name': test,
               'actions':
                   ["coverage run --parallel-mode `which py.test` -v %s" % test,
                    "coverage combine",
                    "coverage report --show-missing %s %s" % (source, test)],
               'verbosity': 2}


############# python3

def task_test3():
    """run unitests on python3"""
    return {'actions': ["py.test-3.2"],
            'verbosity': 2,
            }


############################ website


DOC_ROOT = 'doc/'
DOC_BUILD_PATH = DOC_ROOT + '_build/html/'

def task_epydoc():
    """# generate API docs"""
    target_path = DOC_BUILD_PATH + 'api/'
    return {'actions':[(create_folder, [target_path]),
                       ("epydoc --config %sepydoc.config " % DOC_ROOT +
                        "-o %(targets)s")],
            'file_dep': CODE_FILES,
            'targets': [target_path]}


def task_spell():
    """spell checker for doc files"""
    # spell always return successful code (0)
    # so this checks if the output is empty
    def check_no_output(doc_file):
        cmd = 'hunspell -l -p doc/dictionary.txt %s'
        output = subprocess.check_output(cmd % doc_file, shell=True)
        if len(output) != 0:
            print(output)
            return False

    for doc_file in glob.glob('doc/*.rst'):
        yield {
            'name': doc_file,
            'actions': [(check_no_output, (doc_file,))],
            'file_dep': ['doc/dictionary.txt', doc_file],
            'verbosity': 2,
            }


def task_sphinx():
    """generate website docs (include analytics)"""
    action = "sphinx-build -b html %s -d %s_build/doctrees %s %s"
    opts = "-A include_analytics=1 -A include_gittip=1"
    return {
        'actions': [action % (opts, DOC_ROOT, DOC_ROOT, DOC_BUILD_PATH)],
        'verbosity': 2,
        'task_dep': ['spell'],
        }


def task_website():
    """dodo file create website html files"""
    return {'actions': None,
            'task_dep': ['epydoc', 'sphinx'],
            }

def task_website_update():
    """update website on SITE_PATH
    website is hosted on github-pages
    this task just copy the generated content to SITE_PATH,
    need to commit/push to deploy site.
    """
    SITE_PATH = '../doit-website'
    SITE_URL = 'pydoit.org'
    return {
        'actions': [
            "rsync -avP %s %s" % (DOC_BUILD_PATH, SITE_PATH),
            "echo %s > %s" % (SITE_URL, os.path.join(SITE_PATH, 'CNAME')),
            "touch %s" % os.path.join(SITE_PATH, '.nojekyll'),
            ],
        'task_dep': ['website'],
        }



################### dist


def task_revision():
    """create file with repo rev number"""
    return {'actions': ["hg tip --template '{rev}:{node}' > revision.txt"]}

def task_manifest():
    """create manifest file for distutils """

    def check_version():
        # using a MANIFEST file directly is broken on python2.7
        # http://bugs.python.org/issue11104
        import sys
        assert sys.version_info < (2,7) or sys.version_info > (2,7,2)

    # create manifest will all files under version control without .hg* files
    cmd = """hg manifest | grep -vE ".*\.hg.*" > MANIFEST """
    cmd2 = "echo 'revision.txt' >> MANIFEST"
    return {'actions': [check_version, cmd, cmd2]}

def task_sdist():
    """create source dist package"""
    return {'actions': ["python setup.py sdist"],
            'task_dep': ['revision', 'manifest'],
            }

def task_pypi():
    """upload package to pypi"""
    return {'actions': ["python setup.py sdist upload"],
            'task_dep': ['revision', 'manifest'],
            }




# doit -f ../doit-recipes/deps/deps.py -d . --reporter=executed-only
