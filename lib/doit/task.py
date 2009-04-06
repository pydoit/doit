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
    @ivar folder_dep: (list) 
    @ivar task_dep: (list)
    @ivar file_dep: (list)
    """

    CAPTURE_OUT = False
    CAPTURE_ERR = False

    def __init__(self,name,action,dependencies=(),targets=()):
        """Init."""    
        # dependencies parameter must be a list
        if not(isinstance(dependencies,list) or isinstance(dependencies,tuple)):
            msg = ("%s. paramater 'dependencies' must be a list or " +
                   "tuple got:'%s'%s")
            raise InvalidTask(msg % (name, str(dependencies),type(dependencies)))

        # targets parameter must be a list
        if not(isinstance(targets,list) or isinstance(targets,tuple)):
            msg = ("%s. paramater 'targets' must be a list or tuple " +
                   "got:'%s'%s")
            raise InvalidTask(msg % (name, str(targets),type(targets)))

        self.name = name
        self.action = action
        self.dependencies = dependencies
        self.targets = targets

        # there are 3 kinds of dependencies: file, task, and folder
        self.folder_dep = [] 
        self.task_dep = [] 
        self.file_dep = []
        for dep in self.dependencies:
            # folder dep ends with a '/'
            if dep.endswith('/'):
                self.folder_dep.append(dep)
            # task dep starts with a ':'
            elif dep.startswith(':'):                    
                self.task_dep.append(dep[1:])
            # file dep 
            else:
                self.file_dep.append(dep)

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
 
    def __init__(self,name,action,dependencies=(),targets=()):
        """Init."""
        assert isinstance(action,str),\
            "'action' from CmdTask must be a string."
        BaseTask.__init__(self,name,action,dependencies,targets)

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

    def __init__(self,name,action,dependencies=(),targets=(),args=None,kwargs=None):
        """Init."""
        assert callable(action),"'action' from PythonTask must be a 'callable'."
        BaseTask.__init__(self,name,action,dependencies,targets)
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
        return "Group"

    def __repr__(self):
        return "<GroupTask: %s>"% self.name
