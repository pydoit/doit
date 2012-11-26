#! /usr/bin/env python

import sys

from doit.task import dict_to_task
from doit.cmd_base import TaskLoader
from doit.doit_cmd import DoitMain

my_builtin_task = {
    'name': 'sample_task',
    'actions': ['echo hello from built in'],
    'doc': 'sample doc',
    }

class MyLoader(TaskLoader):
    @staticmethod
    def load_tasks(cmd, opt_values, pos_args):
        task_list = [dict_to_task(my_builtin_task)]
        config = {'verbosity': 2}
        return task_list, config


if __name__ == "__main__":
    sys.exit(DoitMain(MyLoader()).run(sys.argv[1:]))
