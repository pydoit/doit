"""Loads dodo file (a python module) and convert them to 'tasks' """

import os
import sys
import inspect
import types

from .exceptions import InvalidTask, InvalidCommand, InvalidDodoFile
from .task import Task, dict_to_task


# TASK_STRING: (string) prefix used to identify python function
# that are task generators in a dodo file.
TASK_STRING = "task_"


# python2.6 added isgenerator
def isgenerator(obj):
    """Check if object type is a generator.

    @param object: object to test.
    @return: (bool) object is a generator?"""
    return type(obj) is types.GeneratorType


def get_module(dodo_file, cwd=None, seek_parent=False):
    """
    @param dodo_file(str): path to file containing the tasks
    @param cwd(str): path to be used cwd, if None use path from dodo_file
    @param seek_parent(bool): search for dodo_file in parent paths if not found
    @return (module) dodo module
    """
    def exist_or_raise(path):
        if not os.path.exists(path):
            msg = ("Could not find dodo file '%s'.\n" +
                   "Please use '-f' to specify file name.\n")
            raise InvalidDodoFile(msg % path)

    # get absolute path name
    if os.path.isabs(dodo_file):
        dodo_path = dodo_file
        exist_or_raise(dodo_path)
    else:
        if not seek_parent:
            dodo_path = os.path.abspath(dodo_file)
            exist_or_raise(dodo_path)
        else:
            # try to find file in any folder above
            current_dir = os.getcwd()
            dodo_path = os.path.join(current_dir, dodo_file)
            file_name = os.path.basename(dodo_path)
            parent = os.path.dirname(dodo_path)
            while not os.path.exists(dodo_path):
                new_parent = os.path.dirname(parent)
                if new_parent == parent: # reached root path
                    exist_or_raise(dodo_file)
                parent = new_parent
                dodo_path = os.path.join(parent, file_name)

    ## load module dodo file and set environment
    base_path, file_name = os.path.split(dodo_path)
    # make sure dodo path is on sys.path so we can import it
    sys.path.insert(0, base_path)

    if cwd is None:
        # by default cwd is same as dodo.py base path
        full_cwd = base_path
    else:
        # insert specified cwd into sys.path
        full_cwd = os.path.abspath(cwd)
        if not os.path.isdir(full_cwd):
            msg = "Specified 'dir' path must be a directory.\nGot '%s'(%s)."
            raise InvalidCommand(msg % (cwd, full_cwd))
        sys.path.insert(0, full_cwd)

    # file specified on dodo file are relative to cwd
    os.chdir(full_cwd)

    # get module containing the tasks
    # FIXME catche errors here
    return __import__(os.path.splitext(file_name)[0])


def load_task_generators(dodo_module, command_names=()):
    """Loads a python file and extracts its task generator functions.

    The python file is a called "dodo" file.

    @param dodo_module: (module) module containing the tasks
    @param command_names: (list - str) blacklist for task names
    @return (dict):
     - task_list (list) of Tasks in the order they were defined on the file
     - default_tasks (list) of tasks to be executed by default
    """

    # get functions defined in the module and select the task generators
    # a task generator function name starts with the string TASK_STRING
    funcs = []
    prefix_len = len(TASK_STRING)
    # get all functions defined in the module
    for name, ref in inspect.getmembers(dodo_module, inspect.isfunction):
        # ignore functions that are not a task (by its name)
        if not name.startswith(TASK_STRING):
            continue
        # remove TASK_STRING prefix from name
        task_name = name[prefix_len:]
        # tasks cant have name of commands
        if task_name in command_names:
            msg = ("Task can't be called '%s' because this is a command name."+
                   " Please choose another name.")
            raise InvalidDodoFile(msg % task_name)
        # get line number where function is defined
        line = inspect.getsourcelines(ref)[1]
        # add to list task generator functions
        funcs.append((task_name, ref, line))

    # sort by the order functions were defined (line number)
    funcs.sort(key=lambda obj:obj[2])

    # generate all tasks
    task_list = []
    for name, ref, line in funcs:
        task_list.extend(generate_tasks(name, ref(), ref.__doc__))

    doit_config = getattr(dodo_module, 'DOIT_CONFIG', {})
    if not isinstance(doit_config, dict):
        msg = ("DOIT_CONFIG  must be a dict. got:'%s'%s")
        raise InvalidDodoFile(msg % (repr(doit_config), type(doit_config)))

    return {'task_list': task_list,
            'config': doit_config}

def generate_tasks(name, gen_result, gen_doc=None):
    """Create tasks from a task generator result.

    @param name: (string) name of taskgen function
    @param gen_result: value returned by a task generator function
    @param gen_doc: (string/None) docstring from the task generator function
    @return: (tuple) task,list of subtasks
    """
    # task described as a dictionary
    if isinstance(gen_result, dict):
        if 'name' in gen_result:
            raise InvalidTask("Task %s. Only subtasks use field name."%name)

        gen_result['name'] = name

        # Use task generator docstring
        # if no doc present in task dict
        if not 'doc' in gen_result:
            gen_result['doc'] = gen_doc

        return [dict_to_task(gen_result)]

    # a generator
    if isgenerator(gen_result):
        group_task = Task(name, None, doc=gen_doc)
        tasks = [group_task]
        # the generator return subtasks as dictionaries .
        for task_dict in gen_result:
            # check valid input
            if not isinstance(task_dict, dict):
                raise InvalidTask("Task %s must yield dictionaries"% name)

            if 'name' not in task_dict:
                raise InvalidTask("Task %s must contain field name. %s"%
                                  (name,task_dict))
            # name is task.subtask
            task_dict['name'] = "%s:%s"% (name, task_dict.get('name'))
            sub_task = dict_to_task(task_dict)
            sub_task.is_subtask = True
            tasks.append(sub_task)

        # add task dependencies to group task.
        group_task.task_dep = [task.name for task in tasks[1:]]
        return tasks

    raise InvalidTask("Task %s. Must return a dictionary. got %s" %
                      (name, type(gen_result)))


def get_tasks(dodo_file, cwd, seek_parent, command_names):
    """get tasks from dodo_file"""
    dodo_module = get_module(dodo_file, cwd, seek_parent)
    return load_task_generators(dodo_module, command_names)


