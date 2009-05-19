"""Task classes."""

import subprocess, sys
import StringIO
import traceback

from doit import logger


class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass

class TaskFailed(Exception):
    """Task execution was not successful."""
    pass

class TaskError(Exception):
    """Error while trying to execute task."""
    pass

# interface
class BaseTask(object):
    """Base class for all tasks objects

    @cvar CAPTURE_OUT: (bool) stdout from the task to be captured
    @cvar CAPTURE_ERR: (bool) stderr from the task to be captured
    @ivar name string
    @ivar action see derived classes
    @ivar dependencies list of all dependencies
    @ivar targets list of targets
    @ivar folder_dep: (list - string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar run_once: (bool) task without dependencies should run
    """

    CAPTURE_OUT = False
    CAPTURE_ERR = False

    def __init__(self,name,action,dependencies=(),targets=(),setup=None):
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
        self.action = action
        self.dependencies = dependencies
        self.targets = targets
        self.setup = setup
        self.run_once = False
        self.isSubtask = False #TODO document. test

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
        raise InvalidTask("Not Implemented")


    def title(self):
        """String representation on output.

        return: (string)
        """
        return "%s => %s"% (self.name,str(self))


class CmdTask(BaseTask):
    """Command line task. Spawns a new process."""

    def __init__(self,name,action,dependencies=(),targets=(),setup=None):
        """Init."""
        assert isinstance(action,str),\
            "'action' from CmdTask must be a string."
        BaseTask.__init__(self,name,action,dependencies,targets,setup)

    def execute(self):
        # set Popen stream parameters
        if not self.CAPTURE_OUT:
            stdout = None
        else:
            stdout = subprocess.PIPE
        if not self.CAPTURE_ERR:
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
        return "Cmd: %s"% self.action

    def __repr__(self):
        return "<CmdTask: %s - '%s'>"% (self.name,self.action)



class PythonTask(BaseTask):
    """Python task. Execute a python callable.

    @ivar action: (callable) a python callable
    @ivar args: (sequnce) arguments to be passed to the callable
    @ivar kwargs: (dict) dict to be passed to the callable
    """

    def __init__(self,name,action,dependencies=(),targets=(),setup=None,args=None,kwargs=None):
        """Init."""
        assert callable(action),"'action' from PythonTask must be a 'callable'."
        BaseTask.__init__(self,name,action,dependencies,targets,setup)
        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

    def execute(self):
        # set std stream
        if self.CAPTURE_OUT:
            old_stdout = sys.stdout
            sys.stdout = StringIO.StringIO()

        if self.CAPTURE_ERR:
            old_stderr = sys.stderr
            sys.stderr = StringIO.StringIO()

        # execute action / callable
        try:
            # Python2.4
            try:
                result = self.action(*self.args,**self.kwargs)
            except Exception, exception:
                error = TaskError(exception)
                error.originalException = traceback.format_exception(\
                    exception.__class__, exception,sys.exc_info()[2])
                raise error
        finally:
            # restore std streams /log captured streams
            if self.CAPTURE_OUT:
                logger.log('stdout',sys.stdout.getvalue())
                sys.stdout.close()
                sys.stdout = old_stdout

            if self.CAPTURE_ERR:
                logger.log('stderr',sys.stderr.getvalue())
                sys.stderr.close()
                sys.stderr = old_stderr

        # if callable returns false. Task failed
        if not result:
            raise TaskFailed("Python Task failed: '%s' returned %s" %
                             (self.action, result))

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"% str(self.action)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonTask: %s - '%s'>"% (self.name,repr(self.action))



class GroupTask(BaseTask):
    """Do nothing. Used to create group tasks
    Group is actually defined by dependencies.
    """
    def execute(self):
        pass

    def __str__(self):
        return "Group: %s" % ", ".join(self.dependencies)

    def __repr__(self):
        return "<GroupTask: %s>"% self.name



def create_task(name,action,dependencies,targets,setup,*args,**kwargs):
    """ create a BaseTask acording to action type

    @param name: (string) task name
    @param action: value dependes on the type of the task
    @param dependencies: (list of strings) each item is a file path or
    another task (prefixed with ':')
    @param targets: (list of strings) items are file paths.
    @param args: optional positional arguments for task.
    @param kwargs: optional keyword arguments for task.
    """
    # a string.
    if isinstance(action,str):
        return CmdTask(name,action,dependencies,targets,setup)
    # a callable.
    elif callable(action):
        return PythonTask(name,action,dependencies,targets,setup,*args,**kwargs)
    elif action is None:
        return GroupTask(name,action,dependencies,targets,setup)
    else:
        raise InvalidTask("Invalid task type. %s:%s" % (name,action.__class__))

def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict: (dict) task representation as a dict.
    @raise L{InvalidTask}:
    """
    # TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','action','dependencies','targets','args','kwargs','setup')
    # FIXME check field 'name'

    # check required fields
    if 'action' not in task_dict:
        raise InvalidTask("Task %s must contain field action. %s"%
                          (task_dict['name'],task_dict))

    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))

    return create_task(task_dict.get('name'),
                       task_dict.get('action'),
                       task_dict.get('dependencies',[]),
                       task_dict.get('targets',[]),
                       task_dict.get('setup',None),
                       args=task_dict.get('args',[]),
                       kwargs=task_dict.get('kwargs',{}))


