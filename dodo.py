"""dodo file. test + management stuff"""

import glob
import os
import subprocess

import pytest
from pyflakes.api import checkPath


DOIT_CONFIG = {
    'minversion': '0.24.0',
    'default_tasks': ['pyflakes', 'ut'],
#    'backend': 'sqlite3',
    'forget_disable_default': True,
    }

CODE_FILES = glob.glob("doit/*.py")
TEST_FILES = glob.glob("tests/test_*.py")
TESTING_FILES = glob.glob("tests/*.py")
PY_FILES = CODE_FILES + TESTING_FILES


def _check_pyflakes(py_file):
    return not bool(checkPath(py_file))

def task_pyflakes():
    for pattern in ['dodo.py', 'doit/*.py', 'tests/*.py']:
        for py_file in sorted(glob.glob(pattern)):
            yield {
                'name': py_file,
                'actions': [(_check_pyflakes, [py_file])],
                'file_dep': [py_file],
            }

def run_test(test):
    return not bool(pytest.main([test]))
def task_ut():
    """run unit-tests"""
    for test in TEST_FILES:
        yield {'name': test,
               'actions': [(run_test, (test,))],
               'file_dep': PY_FILES,
               'verbosity': 0}


def _coverage_actions(modules, test=None):
    """build coverage run/combine/report commands"""
    omit = ['tests/myecho.py', 'tests/sample_process.py']
    actions = [
        'coverage run --parallel-mode --concurrency multiprocessing'
        ' `which py.test`' + (' ' + test if test else ''),
        'coverage combine',
        'coverage report --show-missing --omit {} {}'.format(
            ','.join(omit), ' '.join(modules)),
    ]
    return actions

def task_coverage():
    """show coverage for all modules including tests"""
    src = glob.glob('doit/*.py')
    tests = glob.glob('tests/*.py')
    all_modules = src + tests

    yield {
        'basename': 'coverage',
        'actions': _coverage_actions(all_modules),
        'verbosity': 2,
    }
    yield {
        'basename': 'coverage_src',
        'actions': _coverage_actions(src),
        'verbosity': 2,
    }
    for test in glob.glob('tests/test_*.py'):
        source = 'doit/' + test[len('tests/test_'):]
        yield {
            'basename': 'coverage_module',
            'name': test,
            'actions': _coverage_actions([source, test], test),
            'verbosity': 2,
        }



############################ website


DOC_ROOT = 'doc/'
DOC_BUILD_PATH = DOC_ROOT + '_build/html/'

def _check_spelling(doc_file, dictionary):
    """run spell checker, return False if misspelled words found"""
    cmd = 'hunspell -l -d en_US -p {} {}'.format(dictionary, doc_file)
    output = subprocess.check_output(cmd, shell=True,
                                     universal_newlines=True)
    if output:
        print(output)
        return False

def task_docs():
    doc_files = [f for f in glob.glob('doc/*.rst') if f != 'doc/index.rst']
    doc_files += ['README.rst', 'CONTRIBUTING.md',
                  'doc/open_collective.md']
    dictionary = 'doc/dictionary.txt'
    for doc_file in doc_files:
        yield {
            'basename': 'spell',
            'name': doc_file,
            'actions': [(_check_spelling, (doc_file, dictionary))],
            'file_dep': [dictionary, doc_file],
            'verbosity': 2,
        }
    sphinx_opts = "-A include_analytics=1 -A include_donate=1"
    yield {
        'basename': 'sphinx',
        'actions': [
            'sphinx-build -b html {} -d {}doctrees {} {}'.format(
                sphinx_opts, DOC_ROOT + '_build/', DOC_ROOT, DOC_BUILD_PATH),
        ],
        'task_dep': ['spell'],
        'verbosity': 2,
    }

def task_samples_check():
    """check samples are at least runnuable without error"""
    black_list = [
        'longrunning.py',  # long running doesn't terminate on its own
        'settrace.py',
        'download.py',  # uses network
        'taskresult.py',  # uses mercurial
        'tar.py',  # uses mercurial
        'calc_dep.py',  # uses files not created by the script
        'report_deps.py',  # uses files not created by the script
        'doit_config.py',  # no tasks defined
    ]
    exclude = set('doc/samples/{}'.format(m) for m in black_list)
    arguments = {'doc/samples/pos.py': 'pos_args -p 4 foo bar'}

    for sample in glob.glob("doc/samples/*.py"):
        if sample in exclude:
            continue
        args = arguments.get(sample, '')
        yield {
            'name': sample,
            'actions': ['doit -f {} {}'.format(sample, args)],
        }


def task_website():
    """dodo file create website html files"""
    return {'actions': None,
            'task_dep': ['sphinx', 'samples_check'],
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



def task_codestyle():
    return {
        'actions': ['pycodestyle doit'],
    }
