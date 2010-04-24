import types
import os

from doit import CatchedException
from doit import cmdparse
from doit.action import create_action, InvalidTask

class Task(object):
    """Task

    @ivar name string
    @ivar actions: list - L{BaseAction}
    @ivar clean_actions: list - L{BaseAction}
    @ivar targets: (list -string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar run_once: (bool) task without dependencies should run
    @ivar run_always: (bool) task always run even if up-to-date
    @ivar setup (list): List of setup objects
          (any object with setup or cleanup method)
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
            modified by runner, value can be: None, run, ignore, up-to-date
    """

    DEFAULT_VERBOSITY = 1

    # list of valid types/values for each task attribute.
    valid_attr = {'name': [str],
                  'actions': [list, tuple, None],
                  'dependencies': [list, tuple],
                  'targets': [list, tuple],
                  'setup': [list, tuple],
                  'clean': [list, tuple, True],
                  'doc': [str, None],
                  'params': [list, tuple],
                  'verbosity': [None,0,1,2],
                  'getargs': [dict],
                  'title': [None, types.FunctionType],
                  }


    def __init__(self, name, actions, dependencies=(), targets=(),
                 setup=(), clean=(), is_subtask=False, doc=None, params=(),
                 verbosity=None, title=None, getargs=None):
        """sanity checks and initialization

        @param params: (list of option parameters) see cmdparse.Command.__init__
        """

        getargs = getargs or {} #default
        # check task attributes input
        for attr, valid_list in self.valid_attr.iteritems():
            self.check_attr_input(name, attr, locals()[attr], valid_list)

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

        self.setup = [] # old setup objects
        self.setup_tasks = [] # new setup tasks
        for setup_item in setup:
            if isinstance(setup_item, str):
                self.setup_tasks.append(setup_item)
            else:
                self.setup.append(setup_item)

        # options
        self.taskcmd = cmdparse.TaskOption(name, params, None, None)
        # put default values on options. this will be overwritten, if params
        # options were passed on the command line.
        self.options = self.taskcmd.parse('')[0] # ignore positional parameters

        # actions
        if actions is None:
            self.actions = []
        else:
            self.actions = [create_action(a) for a in actions]

        # clean
        if clean is True:
            self._remove_targets = True
            self.clean_actions = ()
        else:
            self._remove_targets = False
            self.clean_actions = [create_action(a) for a in clean]

        # set self as task for all actions
        for action in self.actions:
            action.task = self

        self._init_dependencies(dependencies)
        self._init_getargs()
        self._init_doc(doc)

        self.run_status = None


    def _init_dependencies(self, dependencies):
        self.dep_changed = None
        # there are 3 kinds of dependencies: file, task, result
        self.task_dep = []
        self.file_dep = []
        self.result_dep = []
        for dep in dependencies:
            # bool
            if isinstance(dep,bool):
                if dep is True:
                    self.run_once = True
                if dep is False:
                    self.run_always = True
            # string
            elif isinstance(dep,str):
                # task dep starts with a ':'
                if dep.startswith(':'):
                    self.task_dep.append(dep[1:])
                # task-result dep starts with a '?'
                elif dep.startswith('?'):
                    # result_dep are also task_dep.
                    self.task_dep.append(dep[1:])
                    self.result_dep.append(dep[1:])
                # file dep
                else:
                    self.file_dep.append(dep)
            # ignore None values
            elif dep is None:
                continue
            else:
                msg = ("%s. Invalid paramater in 'dependencies' "+
                       "got:'%s(%s)'")
                raise InvalidTask(msg%(self.name, str(dep), type(dep)))


    def _init_getargs(self):
        # getargs also define implicit task dependencies
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

        # run_once can't be used together with file dependencies
        if self.run_once and self.file_dep:
            msg = ("%s. task cant have file and dependencies and True " +
                   "at the same time. (just remove True)")
            raise InvalidTask(msg % self.name)

    def _init_doc(self, doc):
        # Store just first non-empty line as documentation string
        if doc is None:
            self.doc = ''
        else:
            for line in doc.splitlines():
                striped = line.strip()
                if striped:
                    self.doc = striped
                    break
            else:
                self.doc = ''


    @staticmethod
    def check_attr_input(task, attr, value, valid):
        """check input task attribute is correct type/value

        @param task (string): task name
        @param attr (string): attribute name
        @param value: actual input from user
        @param valid (list): of valid types/value accepted
        @raises InvalidTask if invalid input
        """
        msg = "Task %s attribute '%s' must be {%s} got:%r %s"
        for expected in valid:
            # check expected type
            if isinstance(expected, type):
                if isinstance(value, expected):
                    return
            # check expected value
            else:
                if expected is value:
                    return

        # input value didnt match any valid type/value, raise execption
        accept = ", ".join([getattr(v,'__name__',str(v)) for v in valid])
        raise InvalidTask(msg % (task, attr, accept, str(value), type(value)))


    def execute(self, out=None, err=None, verbosity=None):
        """Executes the task.
        @return failure: see CmdAction.execute
        """
        # select verbosity to be used
        priority = (verbosity, # use command line option
                    self.verbosity, # or task default from dodo file
                    self.DEFAULT_VERBOSITY) # or global default
        use_verbosity = [v for v in  priority if v is not None][0]

        VERBOSITY = [(None, None), # 0
                     (None, err),  # 1
                     (out, err)]   # 2
        task_stdout, task_stderr = VERBOSITY[use_verbosity]
        for action in self.actions:
            action_return = action.execute(task_stdout, task_stderr)
            if isinstance(action_return, CatchedException):
                return action_return
            self.result = action.result
            self.values.update(action.values)


    def clean(self, outstream, dryrun):
        """Execute task's clean
        @ivar outstream: 'write' output into this stream
        @ivar dryrun (bool): if True clean tasks are not executed
                             (just print out what would be executed)
        """
        # if clean is True remove all targets
        if self._remove_targets is True:
            files = filter(os.path.isfile, self.targets)
            dirs = filter(os.path.isdir, self.targets)

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
                    outstream.write(msg % (self.name, file_))
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
    for key in task_dict.keys():
        if key not in Task.valid_attr.keys():
            raise InvalidTask("Task %s contains invalid field: '%s'"%
                              (task_dict['name'],key))

    return Task(**task_dict)
