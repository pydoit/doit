"""Tasks are the main abstractions managed by doit"""

import types
import os

from doit import cmdparse
from doit.exceptions import CatchedException, InvalidTask
from doit.action import create_action


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
    @ivar calc_dep: (list - string) reference to a task
    @ivar calc_dep_stack: (list - string) unprocessed calc_dep
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar run_once: (bool) task without dependencies should run
    @ivar run_always: (bool) task always run even if up-to-date
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
    valid_attr = {'name': ([str], []),
                  'actions': ([list, tuple], [None]),
                  'file_dep': ([list, tuple], []),
                  'task_dep': ([list, tuple], []),
                  'result_dep': ([list, tuple], []),
                  'calc_dep': ([list, tuple], []),
                  'targets': ([list, tuple], []),
                  'setup': ([list, tuple], []),
                  'clean': ([list, tuple], [True]),
                  'teardown': ([list, tuple], []),
                  'doc': ([str], [None]),
                  'params': ([list, tuple], []),
                  'verbosity': ([], [None,0,1,2]),
                  'getargs': ([dict], []),
                  'title': ([types.FunctionType], [None]),
                  }


    def __init__(self, name, actions, file_dep=(), targets=(),
                 task_dep=(), result_dep=(), calc_dep=(),
                 setup=(), clean=(), teardown=(), is_subtask=False, doc=None,
                 params=(), verbosity=None, title=None, getargs=None):
        """sanity checks and initialization

        @param params: (list of option parameters) see cmdparse.Command.__init__
        """

        getargs = getargs or {} #default
        # check task attributes input
        my_locals = locals()
        for attr, valid_list in self.valid_attr.iteritems():
            self.check_attr_input(name, attr, my_locals[attr], valid_list)

        self.name = name
        self.targets = targets
        self.run_once = False
        self.run_always = False
        self.is_subtask = is_subtask
        self.result = None
        self.values = {}
        self.verbosity = verbosity
        self.custom_title = title
        self.getargs = getargs
        self.setup_tasks = list(setup)

        # options
        self.taskcmd = cmdparse.TaskOption(name, params, None, None)
        # put default values on options. this will be overwritten, if params
        # options were passed on the command line.
        self.options = self.taskcmd.parse('')[0] # ignore positional parameters

        # actions
        if actions is None:
            self.actions = []
        else:
            self.actions = [create_action(a, self) for a in actions]

        # clean
        if clean is True:
            self._remove_targets = True
            self.clean_actions = ()
        else:
            self._remove_targets = False
            self.clean_actions = [create_action(a, self) for a in clean]

        # teardown
        self.teardown = [create_action(a, self) for a in teardown]

        # dependencies
        self.dep_changed = None

        self.file_dep = set()
        self._expand_file_dep(file_dep)

        # task_dep
        self.task_dep = []
        self.wild_dep = []
        self._expand_task_dep(task_dep)

        # result_dep
        self.result_dep = []
        self._expand_result_dep(result_dep)

        # calc_dep
        self.calc_dep = []
        self.calc_dep_stack = []
        self._expand_calc_dep(calc_dep)

        self._init_getargs()
        self.doc = self._init_doc(doc)

        self.run_status = None


    def _expand_file_dep(self, file_dep):
        """convert file_dep input into file_dep, run_once, run_always"""
        for dep in file_dep:
            # bool
            if isinstance(dep, bool):
                if dep is True:
                    self.run_once = True
                if dep is False:
                    self.run_always = True
            # ignore None values
            elif dep is None:
                continue
            else:
                if dep not in self.file_dep:
                    self.file_dep.add(dep)

        # run_once can't be used together with file dependencies
        if self.run_once and self.file_dep:
            msg = ("%s. task cant have file and dependencies and True " +
                   "at the same time. (just remove True)")
            raise InvalidTask(msg % self.name)


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
                self.calc_dep.append(dep)
                self.calc_dep_stack.append(dep)


    def update_deps(self, deps):
        """expand all kinds of dep input"""
        for dep, dep_values in deps.iteritems():
            if dep == 'task_dep':
                self._expand_task_dep(dep_values)
            elif dep == 'file_dep':
                self._expand_file_dep(dep_values)
            elif dep == 'result_dep':
                self._expand_result_dep(dep_values)
            elif dep == 'calc_dep':
                self._expand_calc_dep(dep_values)


    def _init_getargs(self):
        """task getargs attribute define implicit task dependencies"""
        for key, desc in self.getargs.iteritems():
            # check format
            parts = desc.split('.')
            if len(parts) != 2:
                msg = ("Taskid '%s' - Invalid format for getargs of '%s'.\n" %
                       (self.name, key) +
                       "Should be <taskid>.<argument-name> got '%s'\n" % desc)
                raise InvalidTask(msg)
            if parts[0] not in self.task_dep:
                self.task_dep.append(parts[0])


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
    def check_attr_input(task, attr, value, valid):
        """check input task attribute is correct type/value

        @param task (string): task name
        @param attr (string): attribute name
        @param value: actual input from user
        @param valid (list): of valid types/value accepted
        @raises InvalidTask if invalid input
        """
        value_type = type(value)
        if value_type in valid[0]:
            return
        if value in valid[1]:
            return

        # input value didnt match any valid type/value, raise execption
        msg = "Task '%s' attribute '%s' must be " % (task, attr)
        accept = ", ".join([getattr(v, '__name__', str(v)) for v in
                            (valid[0] + valid[1])])
        msg += "{%s} got:%r %s" % (accept, value, type(value))
        raise InvalidTask(msg)


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
