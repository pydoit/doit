"""dodo file create website html files"""

import glob

srcFiles = glob.glob("lib/doit/*.py")
docRoot = 'doc/'
buildPath = docRoot + '_build/html/'

# generate API docs.
def task_epydoc():
    targetPath = buildPath + 'api/'
    return {'action':"epydoc --config epydoc.config -o %s"% targetPath,
            'dependencies': srcFiles + [targetPath],
            'targets': [targetPath + 'index.html']}

def task_sphinx():
    return "sphinx-build -b html -d %s/_build/doctrees %s %s" % \
        (docRoot, docRoot, buildPath)
    
