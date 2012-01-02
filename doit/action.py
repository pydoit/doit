"""Implements actions used by doit tasks
"""

import subprocess, sys
import StringIO
import inspect
from threading import Thread

from .exceptions import InvalidTask, TaskFailed, TaskError


# Actions
class BaseAction(object):
    """Base class for all actions"""

    # must implement:
    # def execute(self, out=None, err=None)

    pass



class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.

    @ivar action(str): Command to be passed to the shell subprocess.
         It may contain python mapping strings with the keys: dependencies,
         changed and targets. ie. "zip %(targets)s %(changed)s"
    @ivar task(Task): reference to task that contains this action
    """

    def __init__(self, action, task=None): #pylint: disable=W0231
        assert isinstance(action, basestring), "CmdAction must be a string."
        self.action = action
        self.task = task
        self.out = None
        self.err = None
        self.result = None
        self.values = {}


    def _print_process_output(self, process, input_, capture, realtime):
        """read 'input_' untill process is terminated
        write 'input_' content to 'capture' and 'realtime' streams
        """
        if realtime:
            if hasattr(realtime, 'encoding'):
                encoding = realtime.encoding or 'utf-8'
            else:
                encoding = 'utf-8'

        while True:
            # line buffered
            try:
                line = input_.readline().decode('utf-8')
            except:
                process.terminate()
                input_.read()
                raise
            # unbuffered ? process.stdout.read(1)
            if line:
                capture.write(line)
                if realtime:
                    realtime.write(line.encode(encoding))
            if not line and process.poll() != None:
                break


    def execute(self, out=None, err=None):
        """
        Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem
        @return failure:
            - None: if successful
            - TaskError: If subprocess return code is greater than 125
            - TaskFailed: If subprocess return code isn't zero (and
        not greater than 125)
        """
        action = self.expand_action()

        # spawn task process
        process = subprocess.Popen(action, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output = StringIO.StringIO()
        errput = StringIO.StringIO()
        t_out = Thread(target=self._print_process_output,
                       args=(process, process.stdout, output, out))
        t_err = Thread(target=self._print_process_output,
                       args=(process, process.stderr, errput, err))
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        self.out = output.getvalue()
        self.err = errput.getvalue()
        self.result = self.out + self.err

        # make sure process really terminated
        process.wait()

        # task error - based on:
        # http://www.gnu.org/software/bash/manual/bashref.html#Exit-Status
        # it doesnt make so much difference to return as Error or Failed anyway
        if process.returncode > 125:
            return TaskError("Command error: '%s' returned %s" %
                            (action,process.returncode))

        # task failure
        if process.returncode != 0:
            return TaskFailed("Command failed: '%s' returned %s" %
                             (action,process.returncode))


    def expand_action(self):
        """expand action string using task meta informations
        @returns (string) - expanded string after substitution
        """
        if not self.task:
            return self.action

        subs_dict = {'targets' : " ".join(self.task.targets),
                     'dependencies': " ".join(self.task.file_dep)}
        # just included changed if it is set
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)
        # task option parameters
        subs_dict.update(self.task.options)
        return self.action % subs_dict


    def clone(self, task):
        return self.__class__(self.action, task)

    def __str__(self):
        return "Cmd: %s" % self.expand_action()

    def __repr__(self):
        return "<CmdAction: '%s'>"  % self.expand_action()




class Writer(object):
    """write to many streams"""
    def __init__(self, *writers):
        """@param writers - file stream like objects"""
        self.writers = writers

    def write(self, text):
        """write 'text' to all streams"""
        for stream in self.writers:
            stream.write(text)

    def flush(self):
        """flush all streams"""
        for stream in self.writers:
            stream.flush()


class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar py_callable: (callable) Python callable
    @ivar args: (sequence)  Extra arguments to be passed to py_callable
    @ivar kwargs: (dict) Extra keyword arguments to be passed to py_callable
    @ivar task(Task): reference to task that contains this action
    """
    def __init__(self, py_callable, args=None, kwargs=None, task=None):
        #pylint: disable=W0231
        self.py_callable = py_callable
        self.task = task
        self.out = None
        self.err = None
        self.result = None
        self.values = {}

        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

        # check valid parameters
        if not hasattr(self.py_callable, '__call__'):
            msg = "%r PythonAction must be a 'callable' got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if type(self.args) is not tuple and type(self.args) is not list:
            msg = "%r args must be a 'tuple' or a 'list'. got '%s'."
            raise InvalidTask(msg % (self.task, self.args))
        if type(self.kwargs) is not dict:
            msg = "%r kwargs must be a 'dict'. got '%s'"
            raise InvalidTask(msg % (self.task, self.kwargs))


    def _prepare_kwargs(self):
        """
        Prepare keyword arguments (targets, dependencies, changed,
        cmd line options)
        Inspect python callable and add missing arguments:
        - that the callable expects
        - have not been passed (as a regular arg or as keyword arg)
        - are available internally through the task object
        """
        # Return just what was passed in task generator
        # dictionary if the task isn't available
        if not self.task:
            return self.kwargs

        argspec = inspect.getargspec(self.py_callable)
        # named tuples only from python 2.6 :(
        argspec_args = argspec[0]
        argspec_keywords = argspec[2]
        argspec_defaults = argspec[3]
        # use task meta information as extra_args
        extra_args = {'targets': self.task.targets,
                      'dependencies': self.task.file_dep,
                      'changed': self.task.dep_changed}

        # tasks parameter options
        extra_args.update(self.task.options)
        kwargs = self.kwargs.copy()

        for key in extra_args.keys():
            # check key is a positional parameter
            if key in argspec_args:
                arg_pos = argspec_args.index(key)

                # it is forbidden to use default values for this arguments
                # because the user might be unware of this magic.
                if (argspec_defaults and
                    len(argspec_defaults) > (len(argspec_args) - (arg_pos+1))):
                    msg = ("%s.%s: '%s' argument default value not allowed "
                           "(reserved by doit)"
                           % (self.task.name, self.py_callable.__name__, key))
                    raise InvalidTask(msg)

                # if not over-written by value passed in *args use extra_arg
                overwritten = arg_pos < len(self.args)
                if not overwritten:
                    kwargs[key] = extra_args[key]

            # if function has **kwargs include extra_arg on it
            elif argspec_keywords and key not in self.kwargs:
                kwargs[key] = extra_args[key]
        return kwargs


    def execute(self, out=None, err=None):
        """Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem

        @return failure: see CmdAction.execute
        """
        # set std stream
        old_stdout = sys.stdout
        output = StringIO.StringIO()
        old_stderr = sys.stderr
        errput = StringIO.StringIO()

        out_list = [output]
        if out:
            out_list.append(out)
        err_list = [errput]
        if err:
            err_list.append(err)

        sys.stdout = Writer(*out_list)
        sys.stderr = Writer(*err_list)

        kwargs = self._prepare_kwargs()

        # execute action / callable
        try:
            returned_value = self.py_callable(*self.args, **kwargs)
        except Exception, exception:
            return TaskError("PythonAction Error", exception)
        finally:
            # restore std streams /log captured streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.out = output.getvalue()
            self.err = errput.getvalue()

        # if callable returns false. Task failed
        if returned_value is False:
            return TaskFailed("Python Task failed: '%s' returned %s" %
                              (self.py_callable, returned_value))
        elif returned_value is True or returned_value is None:
            pass
        elif isinstance(returned_value, basestring):
            self.result = returned_value
        elif isinstance(returned_value, dict):
            self.values = returned_value
        else:
            return TaskError("Python Task error: '%s'. It must return:\n"
                             "False for failed task.\n"
                             "True, None, string or dict for successful task\n"
                             "returned %s (%s)" %
                             (self.py_callable, returned_value,
                              type(returned_value)))

    def clone(self, task):
        return self.__class__(self.py_callable, self.args, self.kwargs, task)

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"% str(self.py_callable)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonAction: '%s'>"% (repr(self.py_callable))


def create_action(action, task_ref):
    """
    Create action using proper constructor based on the parameter type

    @param action: Action to be created
    @type action: L{BaseAction} subclass object, str, tuple or callable
    @raise InvalidTask: If action parameter type isn't valid
    """
    if isinstance(action, BaseAction):
        action.task = task_ref
        return action

    if isinstance(action, basestring):
        return CmdAction(action, task_ref)

    if isinstance(action, tuple):
        if len(action) > 3:
            msg = "Task '%s': invalid 'actions' tuple length. got:%r %s"
            raise InvalidTask(msg % (task_ref.name, action, type(action)))
        py_callable, args, kwargs = (list(action) + [None]*(3-len(action)))
        return PythonAction(py_callable, args, kwargs, task_ref)

    if hasattr(action, '__call__'):
        return PythonAction(action, task=task_ref)

    msg = "Task '%s': invalid 'actions' type. got:%r %s"
    raise InvalidTask(msg % (task_ref.name, action, type(action)))
