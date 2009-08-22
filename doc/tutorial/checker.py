
pyfile = "sample.py"
def task_checker():
    return {'action': "pychecker %s" % pyfile,
            'dependencies': (pyfile,)}
