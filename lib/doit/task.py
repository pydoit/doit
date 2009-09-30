"""Task and actions classes."""
import subprocess, sys
import StringIO
import traceback
import inspect

from doit import logger


# Exceptions
class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass

# TODO rename this?
class TaskFailed(Exception):
    """Task execution was not successful."""
    pass

class TaskError(Exception):
    """Error while trying to execute task."""
    pass





# Actions
class BaseAction(object):
    """Base class for all actions"""

    # must implement:
    # def execute(self, capture_stdout=False, capture_stderr=False)

    pass



class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.

    @ivar action(str): Command to be passed to the shell subprocess.
         It may contain python mapping strings with the keys: dependencies,
         changed and targets. ie. "zip %(targets)s %(changed)s"
    @ivar task(Task): reference to task that contains this action
    """

    def __init__(self, action):
        assert isinstance(action,str), "CmdAction must be a string."
        self.action = action
        self.task = None


    def execute(self, capture_stdout=False, capture_stderr=False):
        """
        Execute command action

        @param capture_stdout(bool): Capture standard output
        @param capture_err(bool): Capture standard error

        @raise TaskError: If subprocess return code is greater than 125
        @raise TaskFailed: If subprocess return code isn't zero (and
        not greater than 125)
        """
        # set Popen stream parameters
        if not capture_stdout:
            stdout = None
        else:
            stdout = subprocess.PIPE
        if not capture_stderr:
            stderr = None
        else:
            stderr = subprocess.PIPE

        action = self.expand_action()

        # spawn task process
        process = subprocess.Popen(action,stdout=stdout,
                                   stderr=stderr, shell=True)

        # log captured stream
        out,err = process.communicate()
        if out:
            logger.log('stdout',out)
        if err:
            logger.log('stderr',err)

        # task error - based on:
        # http://www.gnu.org/software/bash/manual/bashref.html#Exit-Status
        # it doesnt make so much difference to return as Error or Failed anyway
        if process.returncode > 125:
            raise TaskError("Command error: '%s' returned %s" %
                            (action,process.returncode))

        # task failure
        if process.returncode != 0:
            raise TaskFailed("Command failed: '%s' returned %s" %
                             (action,process.returncode))

    def expand_action(self):
        """expand action string using task meta informations
        @returns (string) - expanded string after substitution
        """
        if not self.task:
            return self.action

        subs_dict = {'targets' : " ".join(self.task.targets),
                     'dependencies': " ".join(self.task.dependencies)}
        # just included changed if it is set
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)
        return self.action % subs_dict


    def __str__(self):
        return "Cmd: %s" % self.expand_action()

    def __repr__(self):
        return "<CmdAction: '%s'>"  % self.expand_action()


class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar py_callable: (callable) Python callable that returns a boolean
    result depending on the success of the action
    @ivar args: (sequence)  Extra arguments to be passed to py_callable
    @ivar kwargs: (dict) Extra keyword arguments to be passed to py_callable
    @ivar task(Task): reference to task that contains this action
    """
    def __init__(self, py_callable, args=None, kwargs=None):

        self.py_callable = py_callable
        self.task = None

        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

        # check valid parameters
        if not callable(self.py_callable):
            raise InvalidTask("PythonAction must be a 'callable'.")
        if type(self.args) is not tuple and type(self.args) is not list:
            msg = "args must be a 'tuple' or a 'list'. got '%s'."
            raise InvalidTask(msg % self.args)
        if type(self.kwargs) is not dict:
            msg = "kwargs must be a 'dict'. got '%s'"
            raise InvalidTask(msg % self.kwargs)


    def _prepare_kwargs(self):
        """
        Prepare keyword arguments (targets, dependencies, changed)
        Inspect python callable and add missing arguments:
        - that the callable expects
        - have not been passed
        - are available internally through the task object
        """
        # Return just what was passed in task generator
        # dictionary if the task isn't available
        if not self.task:
            return self.kwargs

        argspec = inspect.getargspec(self.py_callable)
        extra_args = {'targets': self.task.targets,
                      'dependencies': self.task.dependencies,
                      'changed': self.task.dep_changed}
        kwargs = self.kwargs.copy()

        for key in extra_args.keys():
            arg_defined = argspec.args and key in argspec.args
            if arg_defined:
                index = argspec.args.index(key)
                arg_passed = len(self.args) > index
                default_defined = argspec.defaults and len(argspec.defaults) > (len(argspec.args) - (index+1))

                if default_defined:
                    raise InvalidTask("%s.%s: '%s' argument default value not allowed "
                                      "(reserved by doit)"
                                      % (self.task.name, self.py_callable.__name__, key))
                if not arg_passed:
                    kwargs[key] = extra_args[key]
            elif argspec.keywords:
                kwargs[key] = extra_args[key]

        return kwargs


    def execute(self, capture_stdout=False, capture_stderr=False):
        """
        Execute command action

        @param capture_stdout (bool): Capture standard output
        @param capture_err (bool): Capture standard error

        @raise TaskFailed: If py_callable returns False
        """
        # set std stream
        if capture_stdout:
            old_stdout = sys.stdout
            sys.stdout = StringIO.StringIO()

        if capture_stderr:
            old_stderr = sys.stderr
            sys.stderr = StringIO.StringIO()

        kwargs = self._prepare_kwargs()

        # execute action / callable
        try:
            # Python2.4
            try:
                result = self.py_callable(*self.args,**kwargs)
            # in python 2.4 SystemExit and KeyboardInterrupt subclass
            # from Exception.
            except (SystemExit, KeyboardInterrupt), exp:
                raise

            except Exception, exception:
                error = TaskError(exception)
                error.originalException = traceback.format_exception(\
                    exception.__class__, exception,sys.exc_info()[2])
                raise error
        finally:
            # restore std streams /log captured streams
            if capture_stdout:
                logger.log('stdout',sys.stdout.getvalue())
                sys.stdout.close()
                sys.stdout = old_stdout

            if capture_stderr:
                logger.log('stderr',sys.stderr.getvalue())
                sys.stderr.close()
                sys.stderr = old_stderr

        # if callable returns false. Task failed
        if not result:
            raise TaskFailed("Python Task failed: '%s' returned %s" %
                             (self.py_callable, result))

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"% str(self.py_callable)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonAction: '%s'>"% (repr(self.py_callable))


def create_action(action):
    """
    Create action using proper constructor based on the parameter type

    @param action: Action to be created
    @type action: L{BaseAction} subclass object, str, tuple or callable
    @raise InvalidTask: If action parameter type isn't valid
    """
    if isinstance(action, BaseAction):
        return action

    if type(action) is str:
        return CmdAction(action)

    if type(action) is tuple:
        return PythonAction(*action)

    if callable(action):
        return PythonAction(action)

    msg = "Invalid task action type. got %s"
    raise InvalidTask(msg % (action.__class__))




class Task(object):
    """Task

    @ivar name string
    @ivar actions: (list) of L{BaseAction}
    @ivar dependencies list of all dependencies
    @ivar targets list of targets
    @ivar folder_dep: (list - string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar run_once: (bool) task without dependencies should run
    @ivar is_subtask: (bool) indicate this task is a subtask.
    @ivar doc: (string) task documentation
    """

    def __init__(self,name, actions, dependencies=(),targets=(),setup=None,
                 is_subtask=False, doc=None):
        """sanity checks and initialization"""
        # dependencies parameter must be a list
        if not ((isinstance(dependencies,list)) or
                (isinstance(dependencies,tuple))):
            msg = ("%s. paramater 'dependencies' must be a list or " +
                   "tuple got:'%s'%s")
            raise InvalidTask(msg%(name, str(dependencies),type(dependencies)))

        # targets parameter must be a list
        if not(isinstance(targets,list) or isinstance(targets,tuple)):
            msg = ("%s. paramater 'targets' must be a list or tuple " +
                   "got:'%s'%s")
            raise InvalidTask(msg % (name, str(targets),type(targets)))

        self.name = name
        self.dependencies = dependencies
        self.targets = targets
        self.setup = setup
        self.run_once = False
        self.is_subtask = is_subtask
        self.dep_changed = None

        if actions is None:
            self.actions = []
        elif type(actions) is list:
            self.actions = [create_action(a) for a in actions]
        else:
        ## DEPREACTED ON 0.4 - REMOVE ON 0.5
            #raise Exception("DEPRECATED must be list")
            msg = "DEPRECATION WARNING: task %s actions must be a list."
            print msg % self.name
            self.actions = [create_action(actions)]
        ## DEPRECATION END


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

        # set self as task for all actions
        for action in self.actions:
            action.task = self

        # there are 3 kinds of dependencies: file, task, and folder
        self.folder_dep = []
        self.task_dep = []
        self.file_dep = []
        for dep in self.dependencies:
            # True on the list. set run_once
            if isinstance(dep,bool):
                if not dep:
                    msg = ("%s. bool paramater in 'dependencies' "+
                           "must be True got:'%s'")
                    raise InvalidTask(msg%(name, str(dep)))
                self.run_once = True
            # folder dep ends with a '/'
            elif dep.endswith('/'):
                self.folder_dep.append(dep)
            # task dep starts with a ':'
            elif dep.startswith(':'):
                self.task_dep.append(dep[1:])
            # file dep
            elif isinstance(dep,str):
                self.file_dep.append(dep)

        # run_once can't be used together with file dependencies
        if self.run_once and self.file_dep:
            msg = ("%s. task cant have file and dependencies and True " +
                   "at the same time. (just remove True)")
            raise InvalidTask(msg % name)


    def execute(self, capture_stdout=False, capture_stderr=False):
        """Executes the task.

        @raise TaskFailed: If raised when executing an action
        @raise TaskError: If raised when executing an action
        """
        for action in self.actions:
            action.execute(capture_stdout, capture_stderr)


    def title(self):
        """String representation on output.

        @rtype: str
        @return: Task name and actions
        """
        return "%s => %s"% (self.name, str(self))


    def __str__(self):
        if self.actions:
            return "\n\t".join([str(action) for action in self.actions])

        # A task that contains no actions at all
        # is used as group task
        return "Group: %s" % ", ".join(self.dependencies)

    def __repr__(self):
        return "<Task: %s>"% self.name


def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict (dict): task representation as a dict.
    @raise InvalidTask: If unexpected fields were passed in task_dict
    """
    # TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','actions','dependencies','targets','setup', 'doc')
    # FIXME check field 'name'

    # === DEPRECATED on 0.4 (to be removed on 0.5): START
    # check required fields
    if 'action' in task_dict and 'actions' not in task_dict:
        #raise Exception("DEPRECATED action")
        task_dict['actions'] = task_dict['action']
        del task_dict['action']
        print ("DEPRECATION WARNING: Task %s contains 'action' key. "
               "This will be deprecated in future versions, "
               "please use 'actions' instead" % task_dict['name'])
    # === DEPRECATION: END

    if 'actions' not in task_dict:
        raise InvalidTask("Task %s must contain 'actions' field. %s" %
                          (task_dict['name'],task_dict))

    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))

    return Task(**task_dict)
