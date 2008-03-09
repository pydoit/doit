import subprocess, sys
import StringIO

from doit import logger

class InvalidTask(Exception):pass
class TaskFailed(Exception):pass
class TaskError(Exception):pass

# interface 
class BaseTask(object):
    """Base class for all tasks objects

    @cvar CAPTURE_OUT bool stdout from the task to be captured
    @cvar CAPTURE_ERR bool stderr from the task to be captured
    """

    CAPTURE_OUT = False
    CAPTURE_ERR = False

    def __init__(self,name,action,dependencies=[]):
        """
        @param name string 
        @param action see derived classes
        @param dependencies list of absolute? file paths.
        """
        # dependencies parameter must be a list
        if not(isinstance(dependencies,list) or isinstance(dependencies,tuple)):
            raise InvalidTask("'dependencies' paramater must be a list or tuple got:'%s' => %s"%(str(dependencies),dependencies.__class__))

        self.name = name
        self.action = action
        self.dependencies = dependencies


    def execute(self):
        """raise a TaskFailed or TaskError in case task was not completed"""
        raise InvalidTask("Not Implemented")

    def __str__(self):
        return str(self.action)

    def title(self):
        """return a string representing the task title"""
        return "%s => %s"%(self.name,str(self))



class CmdTask(BaseTask):
    """Command line task. spawn new process."""
 
    def execute(self):
        # set Popen stream parameters
        if not self.CAPTURE_OUT:
            stdout = sys.__stdout__
        else:
            stdout = subprocess.PIPE
        if not self.CAPTURE_ERR:
            stderr = sys.__stderr__
        else:
            stderr = subprocess.PIPE

        # spawn task process
        try:
            p = subprocess.Popen(self.action,stdout=stdout,
                                 stderr=stderr)
        # task error
        except OSError, e:
            raise TaskError("Error trying to execute the command: %s\n" % 
                             " ".join(self.action) + "    error: %s" % e)

        # log captured stream
        out,err = p.communicate()
        if out:
            logger.log('stdout',out)
        if err:
            logger.log('stderr',err)

        # task failure
        if p.returncode != 0:
            raise TaskFailed("Task failed")

            
    def __str__(self):
        return "Cmd: %s"%" ".join(self.action)

    def __repr__(self):
        return "<CmdTask: %s - '%s'>"%(self.name," ".join(self.action))



class PythonTask(BaseTask):
    """Python task. Execute a python callable"""

    def __init__(self,name,action,dependencies=[],args=[],kwargs={}):
        """
        @ivar action callable a python callable
        @ivar args sequnce arguments to be passed to the callable
        @ivar kwargs dict dict to be passed to the callable
        """
        BaseTask.__init__(self,name,action,dependencies)
        self.args = args
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
            result = self.action(*self.args,**self.kwargs)
        except Exception, e:
            raise TaskError(e)
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
            raise TaskFailed("Task failed")
                    
    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"%str(self.action)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonTask: %s - '%s'>"%(self.name,repr(self.action))
