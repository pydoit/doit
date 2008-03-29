"""Automate release process. 

This is "dodo" file (suposed to be run with DoIt).
"""

def task_revision():
    return "bzr version-info > revision.txt"

def task_sdist():
    return "python setup.py sdist"

def task_epydoc():
    return "epydoc --config epydoc.config"
