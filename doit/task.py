import subprocess, sys
import StringIO

from doit import logger

class InvalidTask(Exception):pass
class TaskFailed(Exception):pass
class TaskError(Exception):pass

# interface 
class BaseTask(object):
    CAPTURE_OUT = False
    CAPTURE_ERR = False

    def __init__(self,name,action,dependencies=[]):
        """
        @param name string 
        @param action see derived classes
        @param dependencies list of absolute? file paths.
        """
        # check parameters make sense.
        if not(isinstance(dependencies,list) or isinstance(dependencies,tuple)):
            raise InvalidTask("'dependencies' paramater must be a list or tuple got:'%s' => %s"%(str(dependencies),dependencies.__class__))

        self.name = name
        self.action = action
        self.dependencies = dependencies


    def execute(self):
        """raise a TaskFailed or TaskError in case task was not completed"""
        pass

    def title(self):
        """return a string representing the task title"""
        return "%s => %s"%(self.name,str(self))


class CmdTask(BaseTask):

    def execute(self):
        if not self.CAPTURE_OUT:
            stdout = sys.__stdout__
        else:
            stdout = subprocess.PIPE

        if not self.CAPTURE_ERR:
            stderr = sys.__stderr__
        else:
            stderr = subprocess.PIPE
        
        try:
            p = subprocess.Popen(self.action,stdout=stdout,
                                 stderr=stderr)

        except OSError, e:
            raise TaskError("Error trying to execute the command: %s\n" % 
                             " ".join(self.action) + "    error: %s" % e)

        out,err = p.communicate()
        if out:
            logger.log('stdout',out)
        if err:
            logger.log('stderr',err)
        if p.returncode != 0:
            raise TaskFailed("Task failed")
            
    def __str__(self):
        return "Cmd: %s"%" ".join(self.action)

    def __repr__(self):
        return "<%s cmd:'%s'>"%(self.name," ".join(self.action))

class PythonTask(BaseTask):

    def __init__(self,name,action,dependencies=[],args=[],kwargs={}):
        BaseTask.__init__(self,name,action,dependencies)
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        if self.CAPTURE_OUT:
            old_stdout = sys.stdout
            sys.stdout = StringIO.StringIO()

        if self.CAPTURE_ERR:
            old_stderr = sys.stderr
            sys.stderr = StringIO.StringIO()

        # TODO i guess a common mistake will be to pass a function
        # that returns a generator instead of passing the generator
        # itself. i could have a special test for this case.
        try:
            if not self.action(*self.args,**self.kwargs):
                raise TaskFailed("Task failed")
        finally:
            if self.CAPTURE_OUT:
                logger.log('stdout',sys.stdout.getvalue())
                sys.stdout.close()
                sys.stdout = old_stdout

            if self.CAPTURE_ERR:
                logger.log('stderr',sys.stderr.getvalue())
                sys.stderr.close()
                sys.stderr = old_stderr

            
        
    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"%str(self.action).split('at')[0][1:]

    def __repr__(self):
        return "<%s Python:'%s'>"%(self.name,repr(self.action))
