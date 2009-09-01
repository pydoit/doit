"""Action to be executed in tasks"""
import subprocess, sys
import StringIO
import traceback
from __builtin__ import callable as is_callable

from doit import logger
from doit.exception import TaskError, TaskFailed, InvalidTask

class BaseAction(object):
    pass


class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.
    """

    def __init__(self, action):
        assert isinstance(action,str), \
            "'action' from CmdAction must be a string."
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
        assert is_callable(callable),"'action' from PythonAction must be a 'callable'."

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
    if isinstance(action, BaseAction):
        return action

    if type(action) is str:
        return CmdAction(action)

    if type(action) is tuple:
        return PythonAction(*action)

    if is_callable(action):
        return PythonAction(action)

    raise InvalidTask("Invalid task action type. %s" % (action.__class__))
