### README
# Sample to test doit.get_initial_workdir
# First create a folder named 'sub1'.
# Invoking doit from the root folder will execute both tasks 'base' and 'sub1'.
# Invoking 'doit -k' from path 'sub1' will execute only task 'sub1'
##################

import os

import doit

DOIT_CONFIG = {
    'verbosity': 2,
    'default_tasks': None, # all by default
    }


# change default tasks based on dir from where doit was run
sub1_dir = os.path.join(os.path.dirname(__file__), 'sub1')
if doit.get_initial_workdir() == sub1_dir:
    DOIT_CONFIG['default_tasks'] = ['sub1']


def task_base():
    return {'actions': ['echo root']}

def task_sub1():
    return {'actions': ['echo sub1']}
