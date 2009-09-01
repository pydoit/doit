"""Action to be executed in tasks"""
import subprocess, sys
import StringIO
import traceback
from __builtin__ import callable as is_callable

from doit import logger
from doit.exception import TaskError, TaskFailed, InvalidTask

class BaseAction(object):
    """
    Base class for all action objects

    @cvar CAPTURE_OUT: (bool) stdout from the task to be captured
    @cvar CAPTURE_ERR: (bool) stderr from the task to be captured
    """
    CAPTURE_OUT = False
    CAPTURE_ERR = False

    def __init__(self, action):
        """Init."""
        self.action = action


    def execute(self):
        """Executes the task.

        @raise TaskFailed:
        @raise TaskError:
        """
        raise Exception("Not Implemented")


class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.
    """

    def __init__(self, action):
        assert isinstance(action,str), \
            "'action' from CmdAction must be a string."
        
        BaseAction.__init__(self, action)


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
        return "Cmd: %s" % self.action

    def __repr__(self):
        return "<CmdAction: %s>"  % self.action


class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar action: (callable) a python callable
    @ivar args: (sequnce) arguments to be passed to the callable
    @ivar kwargs: (dict) dict to be passed to the callable
    """
    def __init__(self, callable, args = None, kwargs = None):
        """Init."""
        assert is_callable(callable),"'action' from PythonAction must be a 'callable'."
        BaseAction.__init__(self, callable)

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
        return "<PythonAction: %s>"% (repr(self.action))

        
def create_action(action):
    """
    Create action using proper constructor based on the parameter type
    """
    if isinstance(action, BaseAction):
        return action

    if type(action) is str:
        return CmdAction(action)

    if type(action) is dict:
        return PythonAction(**action)

    if is_callable(action):
        return PythonAction(action)

    raise InvalidTask("Invalid task action type. %s" % (action.__class__))
