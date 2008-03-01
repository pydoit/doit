import subprocess, sys, StringIO, traceback

from odict import OrderedDict

from doit.dependency import Dependency

class InvalidTask(Exception):pass
class TaskFailed(Exception):pass
class TaskError(Exception):pass

# interface 
class BaseTask(object):
    _dependencyManager = None 

    def __init__(self,task,name,dependencies=[]):
        """
        @param task see derived classes
        @param name string 
        @param dependencies list of absolute file paths.
        """
        # check parameters make sense.
        if not(isinstance(dependencies,list) or isinstance(dependencies,tuple)):
            raise InvalidTask("'dependencies' paramater must be a list or tuple got:'%s' => %s"%(str(dependencies),dependencies.__class__))

        self.task = task
        self.name = name
        self.dependencies = dependencies

        if not BaseTask._dependencyManager:
            BaseTask._dependencyManager = Dependency(".doit.dbm")

    def check_execute(self):
        """execute if any dependency was modified
        @return True if executed, False if skipped execution"""
        # always execute task if there is no specified dependency.
        if not self.dependencies:
            self.execute()
            return True
        # check for dependencies before executing
        for d in self.dependencies:
            if self._dependencyManager.modified(self.name,d):
                self.execute()
                self.save_dependencies()
                return True
        return False

    def save_dependencies(self):
        """save dependencies value."""
        for d in self.dependencies:
            self._dependencyManager.save(self.name,d)


    def execute(self):
        """raise a TaskFailed or TaskError in case task was not completed"""
        pass

    def title(self):
        """return a string representing the task title"""
        return "%s => %s"%(self.name,str(self))


class CmdTask(BaseTask):

    def execute(self):
        try:
            p = subprocess.Popen(self.task,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except OSError, e:
            raise TaskError("Error trying to execute the command: %s\n" % 
                             " ".join(self.task) + "    error: %s" % e)

        out,err = p.communicate()
        sys.stdout.write(out)
        sys.stderr.write(err)
        if p.returncode != 0:
            raise TaskFailed("Task failed")
            
    def __str__(self):
        return "Cmd: %s"%" ".join(self.task)

    def __repr__(self):
        return "<%s cmd:'%s'>"%(str(self.__class__)[8:-2]," ".join(self.task))

class PythonTask(BaseTask):

    def execute(self):
        # TODO i guess a common mistake will be to pass a function
        # that returns a generator instead of passing the generator
        # itself. i could have a special test for this case.
        if not self.task():
            raise TaskFailed("Task failed")
        
    def __str__(self):
        return "Python: %s"%str(self.task)

    def __repr__(self):
        return "<%s Python:'%s'>"%(str(self.__class__)[8:-2],repr(self.task))

class Runner(object):
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2

    def __init__(self, verbosity=1):
        """
        verbosity
        # 0 => print (stderr and stdout) from failed tasks
        # 1 => print stderr and (stdout from failed tasks)
        # 2 => print stderr and stdout from all tasks
        """
        self.verbosity = verbosity
        self.success = None
        self._tasks = OrderedDict()

        # set stdout
        self.oldOut = None
        if self.verbosity < 2:
            self.oldOut = sys.stdout 
            sys.stdout = StringIO.StringIO()

        # only if verbosity is 0 we need to capture stderr
        # otherwise we should not supress any message.
        self.oldErr = None
        if self.verbosity == 0:
            self.oldErr = sys.stderr
            sys.stderr = StringIO.StringIO()

    def _addTask(self,task):
        # task must be a BaseTask
        if not isinstance(task,BaseTask):
            raise InvalidTask("Task must an instance of BaseTask class. %s"% 
                              (task.__class__))

        #task name must be unique
        if task.name in self._tasks:
            raise InvalidTask("Task names must be unique. %s"%task.name)
        self._tasks[task.name] = task

    def run(self, printTitle=True):
        """@param print_title bool print task title """
        for task in self._tasks.itervalues():
            # clear previous output
            if self.oldOut:
                sys.stdout = StringIO.StringIO()
            if self.oldErr:
                sys.stderr = StringIO.StringIO()

            try:                
                # print title
                # TODO this is so ugly!
                if printTitle:
                    if self.oldOut:
                        self.oldOut.write("%s\n"%task.title())
                    else:
                        print task.title()
                
            
                task.check_execute()
                #executed = task.check_execute()
                #self.oldOut.write(str(executed))

            # task failed
            except TaskFailed, e:
                self.success = False
                print e
                return self.done(self.FAILURE)
            # task error
            except Exception:
                self.success = False
                return self.done(self.ERROR)
        
        self.success = True
        #done
        return self.done(self.SUCCESS)

    def done(self,result):
        # update dependencies 
        BaseTask._dependencyManager.close()
        BaseTask._dependencyManager = None

        # if test fails
        if result != self.SUCCESS:
            # print stderr if havent printed yet.
            if self.verbosity == 0:
                self.oldErr.write(sys.stderr.getvalue())
            # print stdout if havent printed yet.
            if self.verbosity < 2:
                self.oldOut.write(sys.stdout.getvalue())
        
        # restore out stream
        if self.verbosity < 2:
            sys.stdout.close()
            sys.stdout = self.oldOut

        # restore err stream
        if self.verbosity == 0:
            sys.stderr.close()
            sys.stderr = self.oldErr

        # always show traceback for whatever exception
        if result == self.ERROR:
            sys.stderr.write(traceback.format_exc())
        
        return result
