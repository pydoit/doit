"""dodo file. test + management stuff"""

import glob
import os

import pytest
from doitpy.pyflakes import Pyflakes
from doitpy.coverage import Config, Coverage, PythonPackage
from doitpy import docs
from doitpy.package import Package


DOIT_CONFIG = {
    'minversion': '0.24.0',
    'default_tasks': ['pyflakes', 'ut'],
#    'backend': 'sqlite3',
    }

CODE_FILES = glob.glob("doit/*.py")
TEST_FILES = glob.glob("tests/test_*.py")
TESTING_FILES = glob.glob("tests/*.py")
PY_FILES = CODE_FILES + TESTING_FILES


def task_pyflakes():
    flaker = Pyflakes()
    yield flaker('dodo.py')
    yield flaker.tasks('doit/*.py')
    yield flaker.tasks('tests/*.py')

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


def task_coverage():
    """show coverage for all modules including tests"""
    cov = Coverage([PythonPackage('doit', 'tests')],
                   config=Config(branch=False, parallel=True,
                                 concurrency='multiprocessing',
                          omit=['tests/myecho.py', 'tests/sample_process.py'],)
                   )
    yield cov.all()
    yield cov.src()
    yield cov.by_module()



############################ website


DOC_ROOT = 'doc/'
DOC_BUILD_PATH = DOC_ROOT + '_build/html/'

def task_docs():
    doc_files = glob.glob('doc/*.rst')
    doc_files += ['README.rst', 'CONTRIBUTING.md',
                  'doc/open_collective.md']
    yield docs.spell(doc_files, 'doc/dictionary.txt')
    sphinx_opts = "-A include_analytics=1 -A include_donate=1"
    yield docs.sphinx(DOC_ROOT, DOC_BUILD_PATH, sphinx_opts=sphinx_opts,
                      task_dep=['spell'])

def task_samples_check():
    """check samples are at least runnuable without error"""
    black_list = [
        'longrunning.py',  # long running doesn't terminate on its own
        'settrace.py',
        'download.py',  # uses network
        'taskresult.py',  # uses mercurial
        'tar.py',  # uses mercurial
        'calc_dep.py',  # uses files not created by the script
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



def task_package():
    """create/upload package to pypi"""
    pkg = Package()
    yield pkg.revision_git()
    yield pkg.manifest_git()
    yield pkg.sdist()
    yield pkg.sdist_upload()



# doit -f ../doit-recipes/deps/deps.py -d . --reporter=executed-only
