"""dodo file create website html files"""

import glob
from doit.tools import create_folder

srcFiles = glob.glob("doit/*.py")
docRoot = 'doc/'
buildPath = docRoot + '_build/html/'

# generate API docs.
def task_epydoc():
    targetPath = buildPath + 'api/'
    return {'actions':[(create_folder, [targetPath]),
                       "epydoc --config epydoc.config -o %(targets)s"],
            'file_dep': srcFiles,
            'targets': [targetPath]}

def task_sphinx():
    action = "sphinx-build -b html -d %s_build/doctrees %s %s"
    return {'actions': [action % (docRoot, docRoot, buildPath)]}

