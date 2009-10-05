"""Automate release process.

This is "dodo" file (suposed to be run with doit).
"""

def task_revision():
    return {'actions': ["bzr version-info > revision.txt"]}

def task_manifest():
    cmd = "bzr ls --versioned --recursive > MANIFEST;echo 'revision.txt' >> MANIFEST"
    return {'actions': [cmd]}

def task_sdist():
    return {'actions': ["python setup.py sdist"]}

