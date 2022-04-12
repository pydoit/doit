from doit.cmd_base import Command

class MyCmd(Command):
    name = 'mycmd'
    doc_purpose = 'test extending doit commands'
    doc_usage = '[XXX]'
    doc_description = 'my command description'

    def execute(self, opt_values, pos_args): # pragma: no cover
        print("this command does nothing!")


##############

from doit.task import dict_to_task
from doit.cmd_base import TaskLoader2

my_builtin_task = {
    'name': 'sample_task',
    'actions': ['echo hello from built in'],
    'doc': 'sample doc',
    }

class MyLoader(TaskLoader2):

    def load_doit_config(self):
        return {'verbosity': 2}

    def load_tasks(self, cmd, pos_args):
        return [dict_to_task(my_builtin_task)]

