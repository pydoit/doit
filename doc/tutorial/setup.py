### task setup env. good for functional tests!

class SetupSample(object):
    def __init__(self, server):
        self.server = server

    def setup(self):
        # start server
        pass

    def cleanup(self):
        # stop server
        pass

setupX = SetupSample('x')
setupY = SetupSample('y')

def task_withenvX():
    for fin in ('a','b','c'):
        yield {'name': fin,
               'actions':['echo x'],
               'setup': [setupX]}

def task_withenvY():
    return {'actions':['echo y'],
            'setup': [setupY]}
