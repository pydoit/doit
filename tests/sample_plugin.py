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
from doit.cmd_base import TaskLoader

my_builtin_task = {
    'name': 'sample_task',
    'actions': ['echo hello from built in'],
    'doc': 'sample doc',
    }

class MyLoader(TaskLoader):
    def load_tasks(self, cmd, opt_values, pos_args):
        task_list = [dict_to_task(my_builtin_task)]
        config = {'verbosity': 2}
        return task_list, config
