"""dodo file create website html files"""

import glob

srcFiles = glob.glob("lib/doit/*.py")
docRoot = 'doc/'
buildPath = docRoot + '_build/html/'

# generate API docs.
def task_epydoc():
    targetPath = buildPath + 'api/'
    return {'actions':["epydoc --config epydoc.config -o %s"% targetPath],
            'dependencies': srcFiles + [targetPath],
            'targets': [targetPath + 'index.html']}

def task_sphinx():
    action = "sphinx-build -b html -d %s_build/doctrees %s %s"
    return {'actions': [action % (docRoot, docRoot, buildPath)]}

