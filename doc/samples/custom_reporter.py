from doit.reporter import ConsoleReporter

class MyReporter(ConsoleReporter):
    def execute_task(self, task):
        self.outstream.write('MyReporter --> %s\n' % task.title())

DOIT_CONFIG = {'reporter': MyReporter,
               'verbosity': 2}

def task_sample():
    for x in range(3):
        yield {'name': str(x),
               'actions': ['echo out %d' % x]}
