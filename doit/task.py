"""Tasks are the main abstractions managed by doit"""

import types
import os
import copy

from . import cmdparse
from .exceptions import CatchedException, InvalidTask
from .action import create_action


class Task(object):
    """Task

    @ivar name string
    @ivar actions: list - L{BaseAction}
    @ivar clean_actions: list - L{BaseAction}
    @ivar teardown (list - L{BaseAction})
    @ivar targets: (list -string)
    @ivar task_dep: (list - string)
    @ivar wild_dep: (list - string) task dependency using wildcard *
    @ivar file_dep: (set - string)
    @ivar result_dep: (list -string)
    @ivar calc_dep: (set - string) reference to a task
    @ivar calc_dep_stack: (list - string) unprocessed calc_dep
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar uptodate: (list - bool/None) use bool/computed value instead of
                                       checking dependencies
    @ivar setup_tasks (list - string): references to task-names
    @ivar is_subtask: (bool) indicate this task is a subtask.
    @ivar result: (str) last action "result". used to check task-result-dep
    @ivar values: (dict) values saved by task that might be used by other tasks
    @ivar getargs: (dict) values from other tasks
    @ivar doc: (string) task documentation

    @ivar options: (dict) calculated params values (from getargs and taskopt)
    @ivar taskopt: (cmdparse.Command)
    @ivar custom_title: function reference that takes a task object as
                        parameter and returns a string.
    @ivar run_status (str): contains the result of Dependency.get_status
            modified by runner, value can be:
           - None: not processed yet
           - run: task is selected to be executed (it might be running or
                   waiting for setup)
           - ignore: task wont be executed (user forced deselect)
           - up-to-date: task wont be executed (no need)
           - done: task finished its execution
    """

    DEFAULT_VERBOSITY = 1

    # list of valid types/values for each task attribute.
    valid_attr = {'name': ((str,), ()),
                  'actions': ((list, tuple,), (None,)),
                  'file_dep': ((list, tuple,), ()),
                  'task_dep': ((list, tuple,), ()),
                  'result_dep': ((list, tuple,), ()),
                  'uptodate': ((list, tuple,), ()),
                  'calc_dep': ((list, tuple,), ()),
                  'targets': ((list, tuple,), ()),
                  'setup': ((list, tuple,), ()),
                  'clean': ((list, tuple,), (True,)),
                  'teardown': ((list, tuple,), ()),
                  'doc': ((str,), (None,)),
                  'params': ((list, tuple,), ()),
                  'verbosity': ((), (None,0,1,2,)),
                  'getargs': ((dict,), ()),
                  'title': ((types.FunctionType,), (None,)),
                  }


    def __init__(self, name, actions, file_dep=(), targets=(),
                 task_dep=(), result_dep=(), uptodate=(),
                 calc_dep=(), setup=(), clean=(), teardown=(), is_subtask=False,
                 doc=None, params=(), verbosity=None, title=None, getargs=None):
        """sanity checks and initialization

        @param params: (list of option parameters) see cmdparse.Command.__init__
        """

        getargs = getargs or {} #default
        self.check_attr(name, 'name', name, self.valid_attr['name'])
        self.check_attr(name, 'actions', actions, self.valid_attr['actions'])
        self.check_attr(name, 'file_dep', file_dep, self.valid_attr['file_dep'])
        self.check_attr(name, 'task_dep', task_dep, self.valid_attr['task_dep'])
        self.check_attr(name, 'result_dep', result_dep,
                        self.valid_attr['result_dep'])
        self.check_attr(name, 'uptodate', uptodate, self.valid_attr['uptodate'])
        self.check_attr(name, 'calc_dep', calc_dep, self.valid_attr['calc_dep'])
        self.check_attr(name, 'targets', targets, self.valid_attr['targets'])
        self.check_attr(name, 'setup', setup, self.valid_attr['setup'])
        self.check_attr(name, 'clean', clean, self.valid_attr['clean'])
        self.check_attr(name, 'teardown', teardown, self.valid_attr['teardown'])
        self.check_attr(name, 'doc', doc, self.valid_attr['doc'])
        self.check_attr(name, 'params', params, self.valid_attr['params'])
        self.check_attr(name, 'verbosity', verbosity,
                        self.valid_attr['verbosity'])
        self.check_attr(name, 'getargs', getargs, self.valid_attr['getargs'])
        self.check_attr(name, 'title', title, self.valid_attr['title'])

        self.name = name
        self.taskcmd = cmdparse.TaskOption(name, params, None, None)
        self.options = None
        self.getargs = getargs
        self.setup_tasks = list(setup)
        self._init_deps(file_dep, task_dep, result_dep, calc_dep)
        self.targets = targets
        self.is_subtask = is_subtask
        self.result = None
        self.values = {}
        self.verbosity = verbosity
        self.custom_title = title

        # actions
        self._action_instances = None
        if actions is None:
            self._actions = []
        else:
            self._actions = actions[:]

        # uptodate
        self.uptodate = self._init_uptodate(uptodate) if uptodate else []

        # clean
        if clean is True:
            self._remove_targets = True
            self.clean_actions = ()
        else:
            self._remove_targets = False
            self.clean_actions = [create_action(a, self) for a in clean]

        self.teardown = [create_action(a, self) for a in teardown]
        self.doc = self._init_doc(doc)
        self.run_status = None


    def _init_deps(self, file_dep, task_dep, result_dep, calc_dep):
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

        # result_dep
        self.result_dep = []
        if result_dep:
            self._expand_result_dep(result_dep)

        # calc_dep
        self.calc_dep = set()
        self.calc_dep_stack = []
        if calc_dep:
            self._expand_calc_dep(calc_dep)

        # get args
        if self.getargs:
            self._init_getargs()


    def _init_uptodate(self, items):
        """wrap uptodate callables"""
        uptodate = []
        for item in items:
            if isinstance(item, bool) or item is None:
                uptodate.append((item, None, None))
            elif hasattr(item, '__call__'):
                uptodate.append((item, [], {}))
            elif isinstance(item, tuple):
                call = item[0]
                args = list(item[1]) if len(item)>1 else []
                kwargs = item[2] if len(item)>2 else {}
                uptodate.append((call, args, kwargs))
            else:
                msg = ("%s. task invalid 'uptodate' item '%r'. " +
                       "Must be bool, None, callable or tuple " +
                       "(callable, args, kwargs).")
                raise InvalidTask(msg % (self.name, item))
        return uptodate


    def _expand_file_dep(self, file_dep):
        """put input into file_dep"""
        for dep in file_dep:
            if not isinstance(dep, basestring):
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

    def _expand_result_dep(self, result_dep):
        """convert ressult_dep input into restul_dep and task_dep"""
        self.result_dep.extend(result_dep)
        # result_dep are also task_dep
        self.task_dep.extend(result_dep)


    def _expand_calc_dep(self, calc_dep):
        """calc_dep input"""
        for dep in calc_dep:
            if dep not in self.calc_dep:
                self.calc_dep.add(dep)
                self.calc_dep_stack.append(dep)


    def _extend_uptodate(self, uptodate):
        """add/extend uptodate values"""
        self.uptodate.extend(self._init_uptodate(uptodate))


    # FIXME should support setup also
    _expand_map = {'task_dep': _expand_task_dep,
                   'file_dep': _expand_file_dep,
                   'result_dep': _expand_result_dep,
                   'calc_dep': _expand_calc_dep,
                   'uptodate': _extend_uptodate,
                   }
    def update_deps(self, deps):
        """expand all kinds of dep input"""
        for dep, dep_values in deps.iteritems():
            self._expand_map[dep](self, dep_values)


    def _init_options(self):
        """put default values on options. this will be overwritten, if params
        options were passed on the command line.
        """
        if self.options is None:
            # ignore positional parameters
            self.options = self.taskcmd.parse('')[0]


    def _init_getargs(self):
        """task getargs attribute define implicit task dependencies"""
        self._init_options()
        for key, desc in self.getargs.iteritems():
            # check format
            parts = desc.rsplit('.', 1)
            if len(parts) != 2:
                msg = ("Taskid '%s' - Invalid format for getargs of '%s'.\n" %
                       (self.name, key) +
                       "Should be <taskid>.<argument-name> got '%s'\n" % desc)
                raise InvalidTask(msg)
            if parts[0] not in self.setup_tasks:
                self.setup_tasks.append(parts[0])


    @staticmethod
    def _init_doc(doc):
        """process task "doc" attribute"""
        # store just first non-empty line as documentation string
        if doc is not None:
            for line in doc.splitlines():
                striped = line.strip()
                if striped:
                    return striped
        return ''


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
        self._init_options()
        if self._action_instances is None:
            self._action_instances = [create_action(a, self) for a in self._actions]
        return self._action_instances


    def insert_action(self, call_ref):
        """insert an action to execute before all other actions

        @param call_ref: callable or (callable, args, kwargs)
        This is part of interface to be used by 'uptodate' callables
        """
        self._actions.insert(0, call_ref)


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
        self._init_options()
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
        self._init_options()
        # if clean is True remove all targets
        if self._remove_targets is True:
            files = [path for path in self.targets if os.path.isfile(path)]
            dirs = [path for path in self.targets if os.path.isdir(path)]

            # remove all files
            for file_ in files:
                msg = "%s - removing file '%s'\n" % (self.name, file_)
                outstream.write(msg)
                if not dryrun:
                    os.remove(file_)

            # remove all directories (if empty)
            for dir_ in dirs:
                if os.listdir(dir_):
                    msg = "%s - cannot remove (it is not empty) '%s'\n"
                    outstream.write(msg % (self.name, dir_))
                else:
                    msg = "%s - removing dir '%s'\n"
                    outstream.write(msg % (self.name, dir_))
                    if not dryrun:
                        os.rmdir(dir_)

        else:
            # clean contains a list of actions...
            for action in self.clean_actions:
                msg = "%s - executing '%s'\n"
                outstream.write(msg % (self.name, action))
                if not dryrun:
                    action.execute()


    def title(self):
        """String representation on output.

        @return: (str) Task name and actions
        """
        if self.custom_title:
            return self.custom_title(self)
        return self.name


    def __repr__(self):
        return "<Task: %s>"% self.name


    # when using multiprocessing Tasks are pickled.
    def __getstate__(self):
        """remove attributes that might contain unpickleble content
        mostly probably closures
        """
        to_pickle = self.__dict__.copy()
        del to_pickle['_actions']
        del to_pickle['_action_instances']
        del to_pickle['clean_actions']
        del to_pickle['teardown']
        del to_pickle['custom_title']
        return to_pickle

    def __eq__(self, other):
        return self.name == other.name

    def update_from_pickle(self, pickle_obj):
        """update self with data from pickled Task"""
        self.__dict__.update(pickle_obj.__dict__)

    def clone(self):
        """create a deep copy of this task"""
        inst =  self.__class__.__new__(self.__class__)
        inst.name = self.name
        inst.targets = self.targets[:]
        inst.uptodate = self.uptodate[:]
        inst.is_subtask = self.is_subtask
        inst.result = self.result
        inst.values = self.values.copy()
        inst.verbosity = self.verbosity
        inst.custom_title = self.custom_title
        inst.getargs = copy.copy(self.getargs)
        inst.setup_tasks = self.setup_tasks[:]
        inst.taskcmd = self.taskcmd
        inst.options = copy.copy(self.options)
        inst._actions = self._actions[:]
        inst._action_instances = [a.clone(inst) for a in self.actions]
        inst._remove_targets = self._remove_targets
        inst.clean_actions = [a.clone(inst) for a in self.clean_actions]
        inst.teardown = [a.clone(inst) for a in self.teardown]
        inst.dep_changed = self.dep_changed
        inst.file_dep = copy.copy(self.file_dep)
        inst.task_dep = self.task_dep[:]
        inst.wild_dep = self.wild_dep[:]
        inst.result_dep = self.result_dep[:]
        inst.calc_dep = copy.copy(self.calc_dep)
        inst.calc_dep_stack = self.calc_dep_stack[:]
        inst.doc = self.doc
        inst.run_status = self.run_status
        return inst

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
                          (task_dict['name'],task_dict))

    # user friendly. dont go ahead with invalid input.
    task_attrs = task_dict.keys()
    valid_attrs = set(Task.valid_attr.iterkeys())
    for key in task_attrs:
        if key not in valid_attrs:
            raise InvalidTask("Task %s contains invalid field: '%s'"%
                              (task_dict['name'],key))

    return Task(**task_dict)
