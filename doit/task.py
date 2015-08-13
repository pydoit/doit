
"""Tasks are the main abstractions managed by doit"""

import types
import os
import sys
import inspect
import six
from collections import OrderedDict
from functools import partial

from .cmdparse import CmdOption, TaskParse
from .exceptions import CatchedException, InvalidTask
from .action import create_action, PythonAction
from .dependency import UptodateCalculator


def first_line(doc):
    """extract first non-blank line from text, to extract docstring title"""
    if doc is not None:
        for line in doc.splitlines():
            striped = line.strip()
            if striped:
                return striped
    return ''


class DelayedLoader(object):
    """contains info for delayed creation of tasks from a task-creator

    :ivar creator: reference to task-creator function
    :ivar task_dep: (str) name of task that should be executed before the
                    the loader call the creator function
    :ivar basename: (str) basename used when creating tasks
                   This is used when doit creates new tasks to handle
                   tasks and targets specified on command line
    :ivar target_regex: (str) regex for all targets that this loader tasks
                        will create
    :ivar created: (bool) wheather this creator was already executed or not
    """
    def __init__(self, creator, executed=None, target_regex=None):
        self.creator = creator
        self.task_dep = executed
        self.basename = None
        self.created = False
        self.target_regex = target_regex
        self.regex_groups = OrderedDict()  # task_name:RegexGroup


# used to indicate that a task had DelayedLoader but was already created
DelayedLoaded = False


class Task(object):
    """Task

    @ivar name string
    @ivar actions: list - L{BaseAction}
    @ivar clean_actions: list - L{BaseAction}
    @ivar loader (DelayedLoader)
    @ivar teardown (list - L{BaseAction})
    @ivar targets: (list -string)
    @ivar task_dep: (list - string)
    @ivar wild_dep: (list - string) task dependency using wildcard *
    @ivar file_dep: (set - string)
    @ivar calc_dep: (set - string) reference to a task
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar uptodate: (list - bool/None) use bool/computed value instead of
                                       checking dependencies
    @ivar value_savers (list - callables) that return dicts to be added to
                           task values. Always executed on main process.
                           To be used by `uptodate` implementations.
    @ivar setup_tasks (list - string): references to task-names
    @ivar is_subtask: (bool) indicate this task is a subtask
    @ivar has_subtask: (bool) indicate this task has subtasks
    @ivar result: (str) last action "result". used to check task-result-dep
    @ivar values: (dict) values saved by task that might be used by other tasks
    @ivar getargs: (dict) values from other tasks
    @ivar doc: (string) task documentation

    @ivar options: (dict) calculated params values (from getargs and taskopt)
    @ivar taskopt: (cmdparse.CmdParse)
    @ivar pos_arg: (str) name of parameter in action to receive positional
                     parameters from command line
    @ivar pos_arg_val: (list - str) list of positional parameters values
    @ivar custom_title: function reference that takes a task object as
                        parameter and returns a string.
    """

    DEFAULT_VERBOSITY = 1
    string_types = (str, ) if six.PY3 else (str, unicode)
    # list of valid types/values for each task attribute.
    valid_attr = {'basename': (string_types, ()),
                  'name': (string_types, ()),
                  'actions': ((list, tuple), (None,)),
                  'file_dep': ((list, tuple), ()),
                  'task_dep': ((list, tuple), ()),
                  'uptodate': ((list, tuple), ()),
                  'calc_dep': ((list, tuple), ()),
                  'targets': ((list, tuple), ()),
                  'setup': ((list, tuple), ()),
                  'clean': ((list, tuple), (True,)),
                  'teardown': ((list, tuple), ()),
                  'doc': (string_types, (None,)),
                  'params': ((list, tuple,), ()),
                  'pos_arg': (string_types, (None,)),
                  'verbosity': ((), (None, 0, 1, 2,)),
                  'getargs': ((dict,), ()),
                  'title': ((types.FunctionType,), (None,)),
                  'watch': ((list, tuple), ()),
    }


    def __init__(self, name, actions, file_dep=(), targets=(),
                 task_dep=(), uptodate=(),
                 calc_dep=(), setup=(), clean=(), teardown=(),
                 is_subtask=False, has_subtask=False,
                 doc=None, params=(), pos_arg=None,
                 verbosity=None, title=None, getargs=None,
                 watch=(), loader=None):
        """sanity checks and initialization

        @param params: (list of dict for parameters) see cmdparse.CmdOption
        """

        getargs = getargs or {} #default
        self.check_attr(name, 'name', name, self.valid_attr['name'])
        self.check_attr(name, 'actions', actions, self.valid_attr['actions'])
        self.check_attr(name, 'file_dep', file_dep, self.valid_attr['file_dep'])
        self.check_attr(name, 'task_dep', task_dep, self.valid_attr['task_dep'])
        self.check_attr(name, 'uptodate', uptodate, self.valid_attr['uptodate'])
        self.check_attr(name, 'calc_dep', calc_dep, self.valid_attr['calc_dep'])
        self.check_attr(name, 'targets', targets, self.valid_attr['targets'])
        self.check_attr(name, 'setup', setup, self.valid_attr['setup'])
        self.check_attr(name, 'clean', clean, self.valid_attr['clean'])
        self.check_attr(name, 'teardown', teardown, self.valid_attr['teardown'])
        self.check_attr(name, 'doc', doc, self.valid_attr['doc'])
        self.check_attr(name, 'params', params, self.valid_attr['params'])
        self.check_attr(name, 'pos_arg', pos_arg,
                        self.valid_attr['pos_arg'])
        self.check_attr(name, 'verbosity', verbosity,
                        self.valid_attr['verbosity'])
        self.check_attr(name, 'getargs', getargs, self.valid_attr['getargs'])
        self.check_attr(name, 'title', title, self.valid_attr['title'])
        self.check_attr(name, 'watch', watch, self.valid_attr['watch'])

        self.name = name
        self.params = params # save just for use on command `info`
        self.options = None
        self.pos_arg = pos_arg
        self.pos_arg_val = None # to be set when parsing command line
        self.setup_tasks = list(setup)

        # actions
        self._action_instances = None
        if actions is None:
            self._actions = []
        else:
            self._actions = list(actions[:])

        self._init_deps(file_dep, task_dep, calc_dep)

        # loaders create an implicity task_dep
        self.loader = loader
        if self.loader and self.loader.task_dep:
            self.task_dep.append(loader.task_dep)

        uptodate = uptodate if uptodate else []

        self.getargs = getargs
        if self.getargs:
            uptodate.extend(self._init_getargs())

        self.value_savers = []
        self.uptodate = self._init_uptodate(uptodate)

        self.targets = targets
        self.is_subtask = is_subtask
        self.has_subtask = has_subtask
        self.result = None
        self.values = {}
        self.verbosity = verbosity
        self.custom_title = title

        # clean
        if clean is True:
            self._remove_targets = True
            self.clean_actions = ()
        else:
            self._remove_targets = False
            self.clean_actions = [create_action(a, self) for a in clean]

        self.teardown = [create_action(a, self) for a in teardown]
        self.doc = self._init_doc(doc)
        self.watch = watch


    def _init_deps(self, file_dep, task_dep, calc_dep):
        """init for dependency related attributes"""
        self.dep_changed = None

        # file_dep
        self.file_dep = set()
        self._expand_file_dep(file_dep)

        # task_dep
        self.task_dep = []
        self.wild_dep = []
        if task_dep:
            self._expand_task_dep(task_dep)

        # calc_dep
        self.calc_dep = set()
        if calc_dep:
            self._expand_calc_dep(calc_dep)


    def _init_uptodate(self, items):
        """wrap uptodate callables"""
        uptodate = []
        for item in items:
            # configure task
            if hasattr(item, 'configure_task'):
                item.configure_task(self)

            # check/append uptodate value to task
            if isinstance(item, bool) or item is None:
                uptodate.append((item, None, None))
            elif hasattr(item, '__call__'):
                uptodate.append((item, [], {}))
            elif isinstance(item, tuple):
                call = item[0]
                args = list(item[1]) if len(item) > 1 else []
                kwargs = item[2] if len(item) > 2 else {}
                uptodate.append((call, args, kwargs))
            elif isinstance(item, six.string_types):
                uptodate.append((item, [], {}))
            else:
                msg = ("%s. task invalid 'uptodate' item '%r'. " +
                       "Must be bool, None, str, callable or tuple " +
                       "(callable, args, kwargs).")
                raise InvalidTask(msg % (self.name, item))
        return uptodate


    def _expand_file_dep(self, file_dep):
        """put input into file_dep"""
        for dep in file_dep:
            if not isinstance(dep, six.string_types):
                raise InvalidTask("%s. file_dep must be a str got '%r' (%s)" %
                                  (self.name, dep, type(dep)))
            self.file_dep.add(dep)


    def _expand_task_dep(self, task_dep):
        """convert task_dep input into actaul task_dep and wild_dep"""
        for dep in task_dep:
            if "*" in dep:
                self.wild_dep.append(dep)
            else:
                self.task_dep.append(dep)


    def _expand_calc_dep(self, calc_dep):
        """calc_dep input"""
        for dep in calc_dep:
            if dep not in self.calc_dep:
                self.calc_dep.add(dep)


    def _extend_uptodate(self, uptodate):
        """add/extend uptodate values"""
        self.uptodate.extend(self._init_uptodate(uptodate))


    # FIXME should support setup also
    _expand_map = {
        'task_dep': _expand_task_dep,
        'file_dep': _expand_file_dep,
        'calc_dep': _expand_calc_dep,
        'uptodate': _extend_uptodate,
    }
    def update_deps(self, deps):
        """expand all kinds of dep input"""
        for dep, dep_values in six.iteritems(deps):
            if dep not in self._expand_map:
                continue
            self._expand_map[dep](self, dep_values)


    def init_options(self):
        """Put default values on options.

        This will only be used, if params options were not passed
        on the command line.
        """
        if self.options is None:
            taskcmd = TaskParse([CmdOption(opt) for opt in self.params])
            # ignore positional parameters
            self.options = taskcmd.parse('')[0]


    def _init_getargs(self):
        """task getargs attribute define implicit task dependencies"""
        check_result = set()

        for arg_name, desc in six.iteritems(self.getargs):

            # tuple (task_id, key_name)
            parts = desc
            if isinstance(parts, six.string_types) or len(parts) != 2:
                msg = ("Taskid '%s' - Invalid format for getargs of '%s'.\n" %
                       (self.name, arg_name) +
                       "Should be tuple with 2 elements " +
                       "('<taskid>', '<key-name>') got '%s'\n" % desc)
                raise InvalidTask(msg)

            if parts[0] not in self.setup_tasks:
                check_result.add(parts[0])

        return [result_dep(t) for t in check_result]


    @staticmethod
    def _init_doc(doc):
        """process task "doc" attribute"""
        # store just first non-empty line as documentation string
        return first_line(doc)

    @staticmethod
    def check_attr(task, attr, value, valid):
        """check input task attribute is correct type/value

        @param task (string): task name
        @param attr (string): attribute name
        @param value: actual input from user
        @param valid (list): of valid types/value accepted
        @raises InvalidTask if invalid input
        """
        if type(value) in valid[0]:
            return
        if value in valid[1]:
            return

        # input value didnt match any valid type/value, raise execption
        msg = "Task '%s' attribute '%s' must be " % (task, attr)
        accept = ", ".join([getattr(v, '__name__', str(v)) for v in
                            (valid[0] + valid[1])])
        msg += "{%s} got:%r %s" % (accept, value, type(value))
        raise InvalidTask(msg)


    @property
    def actions(self):
        """lazy creation of action instances"""
        if self._action_instances is None:
            self._action_instances = [
                create_action(a, self) for a in self._actions]
        return self._action_instances


    def save_extra_values(self):
        """run value_savers updating self.values"""
        for value_saver in self.value_savers:
            self.values.update(value_saver())


    def _get_out_err(self, out, err, verbosity):
        """select verbosity to be used"""
        priority = (verbosity, # use command line option
                    self.verbosity, # or task default from dodo file
                    self.DEFAULT_VERBOSITY) # or global default
        use_verbosity = [v for v in  priority if v is not None][0]

        out_err = [(None, None), # 0
                   (None, err),  # 1
                   (out, err)]   # 2
        return out_err[use_verbosity]


    def execute(self, out=None, err=None, verbosity=None):
        """Executes the task.
        @return failure: see CmdAction.execute
        """
        self.init_options()
        task_stdout, task_stderr = self._get_out_err(out, err, verbosity)
        for action in self.actions:
            action_return = action.execute(task_stdout, task_stderr)
            if isinstance(action_return, CatchedException):
                return action_return
            self.result = action.result
            self.values.update(action.values)


    def execute_teardown(self, out=None, err=None, verbosity=None):
        """Executes task's teardown
        @return failure: see CmdAction.execute
        """
        task_stdout, task_stderr = self._get_out_err(out, err, verbosity)
        for action in self.teardown:
            action_return = action.execute(task_stdout, task_stderr)
            if isinstance(action_return, CatchedException):
                return action_return


    def clean(self, outstream, dryrun):
        """Execute task's clean
        @ivar outstream: 'write' output into this stream
        @ivar dryrun (bool): if True clean tasks are not executed
                             (just print out what would be executed)
        """
        self.init_options()
        # if clean is True remove all targets
        if self._remove_targets is True:
            clean_targets(self, dryrun)
        else:
            # clean contains a list of actions...
            for action in self.clean_actions:
                msg = "%s - executing '%s'\n"
                outstream.write(msg % (self.name, action))

                # add extra arguments used by clean actions
                if isinstance(action, PythonAction):
                    action_args = inspect.getargspec(action.py_callable).args
                    if 'dryrun' in action_args:
                        action.kwargs['dryrun'] = dryrun

                if not dryrun:
                    result = action.execute(out=outstream)
                    if isinstance(result, CatchedException):
                        sys.stderr.write(str(result))

    def title(self):
        """String representation on output.

        @return: (str) Task name and actions
        """
        if self.custom_title:
            return self.custom_title(self)
        return self.name


    def __repr__(self):
        return "<Task: %s>"% self.name


    def __getstate__(self):
        """remove attributes that never used on process that only execute tasks
        """
        to_pickle = self.__dict__.copy()
        # never executed in sub-process
        to_pickle['uptodate'] = None
        to_pickle['value_savers'] = None
        # can be re-recreated on demand
        to_pickle['_action_instances'] = None
        return to_pickle

    # when using multiprocessing Tasks are pickled.
    def pickle_safe_dict(self):
        """remove attributes that might contain unpickleble content
        mostly probably closures
        """
        to_pickle = self.__dict__.copy()
        del to_pickle['_actions']
        del to_pickle['_action_instances']
        del to_pickle['clean_actions']
        del to_pickle['teardown']
        del to_pickle['custom_title']
        del to_pickle['value_savers']
        del to_pickle['uptodate']
        return to_pickle

    def update_from_pickle(self, pickle_obj):
        """update self with data from pickled Task"""
        self.__dict__.update(pickle_obj)

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        """used on default sorting of tasks (alphabetically by name)"""
        return self.name < other.name



def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict (dict): task representation as a dict.
    @raise InvalidTask: If unexpected fields were passed in task_dict
    """
    # check required fields
    if 'actions' not in task_dict:
        raise InvalidTask("Task %s must contain 'actions' field. %s" %
                          (task_dict['name'], task_dict))

    # user friendly. dont go ahead with invalid input.
    task_attrs = list(six.iterkeys(task_dict))
    valid_attrs = set(six.iterkeys(Task.valid_attr))
    for key in task_attrs:
        if key not in valid_attrs:
            raise InvalidTask("Task %s contains invalid field: '%s'"%
                              (task_dict['name'], key))

    return Task(**task_dict)



def clean_targets(task, dryrun):
    """remove all targets from a task"""
    files = [path for path in task.targets if os.path.isfile(path)]
    dirs = [path for path in task.targets if os.path.isdir(path)]

    # remove all files
    for file_ in files:
        six.print_("%s - removing file '%s'" % (task.name, file_))
        if not dryrun:
            os.remove(file_)

    # remove all directories (if empty)
    for dir_ in dirs:
        if os.listdir(dir_):
            msg = "%s - cannot remove (it is not empty) '%s'"
            six.print_(msg % (task.name, dir_))
        else:
            msg = "%s - removing dir '%s'"
            six.print_(msg % (task.name, dir_))
            if not dryrun:
                os.rmdir(dir_)


def _return_param(val):
    '''just return passed parameter - make a callable from any value'''
    return val

# uptodate
class result_dep(UptodateCalculator):
    """check if result of the given task was modified
    """
    def __init__(self, dep_task_name):
        self.dep_name = dep_task_name
        self.result_name = '_result:%s' % self.dep_name

    def configure_task(self, task):
        """to be called by doit when create the task"""
        # result_dep creates an implicit task_dep
        task.setup_tasks.append(self.dep_name)

    def _result_single(self):
        """get result from a single task"""
        return self.get_val(self.dep_name, 'result:')

    def _result_group(self, dep_task):
        """get result from a group task
        the result is the combination of results of all sub-tasks
        """
        prefix = dep_task.name + ":"
        sub_tasks = {}
        for sub in dep_task.task_dep:
            if sub.startswith(prefix):
                sub_tasks[sub] = self.get_val(sub, 'result:')
        return sub_tasks

    def __call__(self, task, values):
        """return True if result is the same as last run"""
        dep_task = self.tasks_dict[self.dep_name]
        if not dep_task.has_subtask:
            dep_result = self._result_single()
        else:
            dep_result = self._result_group(dep_task)
        func = partial(_return_param, {self.result_name: dep_result})
        task.value_savers.append(func)

        last_success = values.get(self.result_name)
        if last_success is None:
            return False
        return last_success == dep_result
