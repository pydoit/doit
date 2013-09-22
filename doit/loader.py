"""Loads dodo file (a python module) and convert them to 'tasks' """

import os
import sys
import inspect
import six

import doit
from .compat import is_bound_method
from .exceptions import InvalidTask, InvalidCommand, InvalidDodoFile
from .task import Task, dict_to_task


# TASK_STRING: (string) prefix used to identify python function
# that are task generators in a dodo file.
TASK_STRING = "task_"


def flat_generator(gen, gen_doc=''):
    """return only values from generators
    if any generator yields another generator it is recursivelly called
    """
    for item in gen:
        if inspect.isgenerator(item):
            item_doc = item.gi_code.co_consts[0]
            for value, value_doc in flat_generator(item, item_doc):
                yield value, value_doc
        else:
            yield item, gen_doc


def get_module(dodo_file, cwd=None, seek_parent=False):
    """
    The python file defining tasks is called "dodo" file.

    @param dodo_file(str): path to file containing the tasks
    @param cwd(str): path to be used cwd, if None use path from dodo_file
    @param seek_parent(bool): search for dodo_file in parent paths if not found
    @return (module) dodo module
    """
    doit.initial_workdir = os.getcwd()
    def exist_or_raise(path):
        """raise exception if file on given path doesnt exist"""
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
            current_dir = doit.initial_workdir
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
    return __import__(os.path.splitext(file_name)[0])


def load_tasks(dodo_module, command_names=()):
    """Get task generators and generate tasks

    @param dodo_module: (dict) containing the task generators, it might
                        contain other stuff
    @param command_names: (list - str) blacklist for task names
    @return task_list (list) of Tasks in the order they were defined on the file
    """

    # get functions defined in the module and select the task generators
    # a task generator function name starts with the string TASK_STRING
    funcs = []
    prefix_len = len(TASK_STRING)
    # get all functions defined in the module
    for name, ref in six.iteritems(dodo_module):

        # function is a task creator because of its name
        if inspect.isfunction(ref) and name.startswith(TASK_STRING):
            # remove TASK_STRING prefix from name
            task_name = name[prefix_len:]

        # object is a task creator because it contains the special method
        elif hasattr(ref, 'create_doit_tasks'):
            ref = ref.create_doit_tasks
            # If create_doit_tasks is a method, it should be called only
            # if it is bounded to an object.
            # This avoids calling it for the class definition.
            argspec = inspect.getargspec(ref)
            if len(argspec.args) != (1 if is_bound_method(ref) else 0):
                continue
            task_name = name

        # ignore functions that are not a task creator
        elif True: # coverage can't get "else: continue"
            continue

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
    # TODO: this ordering doesnt make sense when generators come
    # from different modules
    funcs.sort(key=lambda obj:obj[2])

    task_list = []
    for name, ref, line in funcs:
        task_list.extend(generate_tasks(name, ref(), ref.__doc__))
    return task_list


def load_doit_config(dodo_module):
    """
    @param dodo_module (dict) dict with module members
    """
    doit_config = dodo_module.get('DOIT_CONFIG', {})
    if not isinstance(doit_config, dict):
        msg = ("DOIT_CONFIG  must be a dict. got:'%s'%s")
        raise InvalidDodoFile(msg % (repr(doit_config), type(doit_config)))
    return doit_config


def _generate_task_from_return(func_name, task_dict, gen_doc):
    """generate a single task from a dict return'ed by a task generator"""
    if 'name' in task_dict:
        raise InvalidTask("Task '%s'. Only subtasks use field name." %
                          func_name)

    task_dict['name'] = task_dict.pop('basename', func_name)

    # Use task generator docstring
    # if no doc present in task dict
    if not 'doc' in task_dict:
        task_dict['doc'] = gen_doc

    return dict_to_task(task_dict)


def _generate_task_from_yield(tasks, func_name, task_dict, gen_doc):
    """generate a single task from a dict yield'ed by task generator

    @param tasks: dictionary with created tasks
    @return None: the created task is added to 'tasks' dict
    """
    # check valid input
    if not isinstance(task_dict, dict):
        raise InvalidTask("Task '%s' must yield dictionaries" %
                          func_name)

    msg_dup = "Task generation '%s' has duplicated definition of '%s'"
    basename = task_dict.pop('basename', None)
    # if has 'name' this is a sub-task
    if 'name' in task_dict:
        basename = basename or func_name
        # if subname is None attributes from group task
        if task_dict['name'] is None:
            task_dict['name'] = basename
            task_dict['actions'] = None
            group_task = dict_to_task(task_dict)
            group_task.has_subtask = True
            tasks[basename] = group_task
            return

        # name is '<task>.<subtask>'
        full_name = "%s:%s"% (basename, task_dict['name'])
        if full_name in tasks:
            raise InvalidTask(msg_dup % (func_name, full_name))
        task_dict['name'] = full_name
        sub_task = dict_to_task(task_dict)
        sub_task.is_subtask = True

        # get/create task group
        group_task = tasks.get(basename)
        if group_task:
            if not group_task.has_subtask:
                raise InvalidTask(msg_dup % (func_name, basename))
        else:
            group_task = Task(basename, None, doc=gen_doc, has_subtask=True)
            tasks[basename] = group_task
        group_task.task_dep.append(sub_task.name)
        tasks[sub_task.name] = sub_task
    # NOT a sub-task
    else:
        if not basename:
            raise InvalidTask(
                "Task '%s' must contain field 'name' or 'basename'. %s"%
                (func_name, task_dict))
        if basename in tasks:
            raise InvalidTask(msg_dup % (func_name, basename))
        task_dict['name'] = basename
        # Use task generator docstring if no doc present in task dict
        if not 'doc' in task_dict:
            task_dict['doc'] = gen_doc
        tasks[basename] = dict_to_task(task_dict)


def generate_tasks(func_name, gen_result, gen_doc=None):
    """Create tasks from a task generator result.

    @param func_name: (string) name of taskgen function
    @param gen_result: value returned by a task generator function
                       it can be a dict or generator (generating dicts)
    @param gen_doc: (string/None) docstring from the task generator function
    @return: (tuple) task, list of subtasks
    """
    # task described as a dictionary
    if isinstance(gen_result, dict):
        return [_generate_task_from_return(func_name, gen_result, gen_doc)]

    # a generator
    if inspect.isgenerator(gen_result):
        tasks = {} # task_name: task
        # the generator return subtasks as dictionaries
        for task_dict, x_doc in flat_generator(gen_result, gen_doc):
            _generate_task_from_yield(tasks, func_name, task_dict, x_doc)

        if tasks:
            return list(six.itervalues(tasks))
        else:
            # special case task_generator did not generate any task
            # create an empty group task
            return [Task(func_name, None, doc=gen_doc, has_subtask=True)]

    if gen_result is None:
        return ()

    raise InvalidTask(
        "Task '%s'. Must return a dictionary or generator. Got %s" %
        (func_name, type(gen_result)))
