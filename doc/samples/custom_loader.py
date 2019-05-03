#! /usr/bin/env python3

import sys

from doit.task import dict_to_task
from doit.cmd_base import TaskLoader2
from doit.doit_cmd import DoitMain

my_builtin_task = {
    'name': 'sample_task',
    'actions': ['echo hello from built in'],
    'doc': 'sample doc',
}


class MyLoader(TaskLoader2):
    def setup(self, opt_values):
        pass

    def load_doit_config(self):
        return {'verbosity': 2}

    def load_tasks(self, cmd, pos_args):
        task_list = [dict_to_task(my_builtin_task)]
        return task_list


if __name__ == "__main__":
    sys.exit(DoitMain(MyLoader()).run(sys.argv[1:]))
