"""Task and action classes."""
import subprocess, sys
import StringIO
import traceback
from __builtin__ import callable as is_callable

from doit import logger

# Exceptions
class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass

class TaskFailed(Exception):
    """Task execution was not successful."""
    pass

class TaskError(Exception):
    """Error while trying to execute task."""
    pass

# Tasks
class Task(object):
    """Base class for all tasks objects

    @ivar name string
    @ivar action see derived classes
    @ivar dependencies list of all dependencies
    @ivar targets list of targets
    @ivar folder_dep: (list - string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar run_once: (bool) task without dependencies should run
    @ivar is_subtask: (bool) indicate this task is a subtask.
    """

    def __init__(self,name,actions,dependencies=(),targets=(),setup=None,
                 is_subtask=False):
        """Init."""
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

        if type(actions) is list:
            self.actions = [create_action(a) for a in actions]
        else:
            self.actions = [create_action(actions)]

        self.dependencies = dependencies
        self.targets = targets
        self.setup = setup
        self.run_once = False
        self.is_subtask = is_subtask

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


    def execute(self):
        """Executes the task.

        @raise TaskFailed:
        @raise TaskError:
        """
        for action in self.actions:
            action.execute()


    def title(self):
        """String representation on output.

        return: (string)
        """
        return "%s => %s"% (self.name,str(self))


    def __str__(self):
        return "\n\t".join([str(action) for action in self.actions])

    def __repr__(self):
        return "<Task: %s>"% self.name


def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict: (dict) task representation as a dict.
    @raise L{InvalidTask}:
    """
    # TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','actions','dependencies','targets','setup')
    # FIXME check field 'name'

    # check required fields
    if 'actions' not in task_dict:
        if 'action' in task_dict:
            task_dict['actions'] = task_dict['action']
            del task_dict['action']
            print ("WARNING Task %s contains 'action' key. "
                   "This will be deprecated in future versions, "
                   "please use 'actions' instead" % task_dict['name'])
        else:
            raise InvalidTask("Task %s must contain 'actions' field. %s" %
                              (task_dict['name'],task_dict))

    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))

    return Task(task_dict.get('name'),
                task_dict.get('actions'),
                task_dict.get('dependencies',[]),
                task_dict.get('targets',[]),
                task_dict.get('setup',None),
                )

# Actions
class BaseAction(object):
    pass


class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.
    """

    def __init__(self, action):
        assert isinstance(action,str), \
            "CmdAction must be a string."
        self.action = action

    def execute(self, capture_stdout = False, capture_stderr = False):
        # set Popen stream parameters
        if not capture_stdout:
            stdout = None
        else:
            stdout = subprocess.PIPE
        if not capture_stderr:
            stderr = None
        else:
            stderr = subprocess.PIPE

        # spawn task process
        process = subprocess.Popen(self.action,stdout=stdout,
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
                            (self.action,process.returncode))

        # task failure
        if process.returncode != 0:
            raise TaskFailed("Command failed: '%s' returned %s" %
                             (self.action,process.returncode))

    def __str__(self):
        return "Cmd: %s" % self.action

    def __repr__(self):
        return "<CmdAction: %s>"  % self.action


class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar action: (callable) a python callable
    @ivar args: (sequence) arguments to be passed to the callable
    @ivar kwargs: (dict) dict to be passed to the callable
    """
    def __init__(self, callable, args = None, kwargs = None):
        """Init."""
        assert is_callable(callable),"PythonAction must be a 'callable'."

        self.callable = callable
        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

    def execute(self, capture_stdout = False, capture_stderr = False):
        # set std stream
        if capture_stdout:
            old_stdout = sys.stdout
            sys.stdout = StringIO.StringIO()

        if capture_stderr:
            old_stderr = sys.stderr
            sys.stderr = StringIO.StringIO()

        # execute action / callable
        try:
            # Python2.4
            try:
                result = self.callable(*self.args,**self.kwargs)
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
                             (self.callable, result))

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"% str(self.callable)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonAction: %s>"% (repr(self.action))

        
def create_action(action):
    """
    Create action using proper constructor based on the parameter type
    """
    # Don't change a subclass object from BaseAction
    # this way any custom action can be written in the future
    # without tying it to a python standard type
    if isinstance(action, BaseAction):
        return action

    if type(action) is str:
        return CmdAction(action)

    if type(action) is tuple:
        return PythonAction(*action)

    if is_callable(action):
        return PythonAction(action)

    raise InvalidTask("Invalid task action type. %s" % (action.__class__))
