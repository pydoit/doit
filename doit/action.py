"""Implements actions used by doit tasks
"""

import subprocess, sys
import six
from six import StringIO
import inspect
from threading import Thread

from .exceptions import InvalidTask, TaskFailed, TaskError


def normalize_callable(ref):
    """return a list with (callabe, *args, **kwargs)
    ref can be a simple callable or a tuple
    """
    if isinstance(ref, tuple):
        return list(ref)
    return [ref, (), {}]

# Actions
class BaseAction(object):
    """Base class for all actions"""

    # must implement:
    # def execute(self, out=None, err=None)

    @staticmethod
    def _prepare_kwargs(task, func, args, kwargs):
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
        if not task:
            return kwargs

        try:
            argspec = inspect.getargspec(func)
        except TypeError:
            argspec = inspect.getargspec(func.__call__)
        # use task meta information as extra_args
        meta_args = {
            'task': task,
            'targets': task.targets,
            'dependencies': task.file_dep,
            'changed': task.dep_changed,
            }

        extra_args = dict(meta_args)
        # tasks parameter options
        extra_args.update(task.options)
        kwargs = kwargs.copy()

        for key in six.iterkeys(extra_args):
            # check key is a positional parameter
            if key in argspec.args:
                arg_pos = argspec.args.index(key)

                # it is forbidden to use default values for this arguments
                # because the user might be unware of this magic.
                if (key in meta_args and argspec.defaults and
                    len(argspec.defaults) > (len(argspec.args) - (arg_pos+1))):
                    msg = ("Task %s, action %s(): The argument '%s' is not "
                           "allowed  to have a default value (reserved by doit)"
                           % (task.name, func.__name__, key))
                    raise InvalidTask(msg)

                # if not over-written by value passed in *args use extra_arg
                overwritten = arg_pos < len(args)
                if not overwritten:
                    kwargs[key] = extra_args[key]

            # if function has **kwargs include extra_arg on it
            elif argspec.keywords and key not in kwargs:
                kwargs[key] = extra_args[key]
        return kwargs



class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.

    @ivar action(str,list,callable): subprocess command string or string list,
         see subprocess.Popen first argument.
         It may also be a callable that generates the command string.
         Strings may contain python mappings with the keys: dependencies,
         changed and targets. ie. "zip %(targets)s %(changed)s"
    @ivar task(Task): reference to task that contains this action
    @ivar save_out: (str) name used to save output in `values`
    @ivar shell: use shell to execute command
                 see subprocess.Popen `shell` attribute
    @ivar pkwargs: Popen arguments except 'stdout' and 'stderr'
    """

    def __init__(self, action, task=None, save_out=None, shell=True,
                 **pkwargs): #pylint: disable=W0231
        for forbidden in ('stdout', 'stderr'):
            if forbidden in pkwargs:
                msg = "CmdAction can't take param named '{0}'."
                raise InvalidTask(msg.format(forbidden))
        self._action = action
        self.task = task
        self.out = None
        self.err = None
        self.result = None
        self.values = {}
        self.save_out = save_out
        self.shell = shell
        self.pkwargs = pkwargs

    @property
    def action(self):
        if isinstance(self._action, (six.string_types, list)):
            return self._action
        else:
            # action can be a callable that returns a string command
            ref, args, kw = normalize_callable(self._action)
            kwargs = self._prepare_kwargs(self.task, ref, args, kw)
            return ref(*args, **kwargs)


    def _print_process_output(self, process, input_, capture, realtime):
        """read 'input_' untill process is terminated
        write 'input_' content to 'capture' and 'realtime' streams
        """
        if realtime:
            if hasattr(realtime, 'encoding'):
                encoding = realtime.encoding or 'utf-8'
            else: # pragma: no cover
                encoding = 'utf-8'

        while True:
            # line buffered
            try:
                line = input_.readline().decode('utf-8')
            except:
                process.terminate()
                input_.read()
                raise
            if not line:
                break
            capture.write(line)
            if realtime:
                if sys.version > '3': # pragma: no cover
                    realtime.write(line)
                else:
                    realtime.write(line.encode(encoding))


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
        try:
            action = self.expand_action()
        except Exception as exc:
            return TaskError("CmdAction Error creating command string", exc)

        # spawn task process
        process = subprocess.Popen(
            action, shell=self.shell,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **self.pkwargs)

        output = StringIO()
        errput = StringIO()
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

        # save stdout in values
        if self.save_out:
            self.values[self.save_out] = self.out


    def expand_action(self):
        """expand action string using task meta informations
        @returns (string) - expanded string after substitution
        """
        if not self.task:
            return self.action

        # cant expand keywords if action is a list of strings
        if isinstance(self.action, list):
            return self.action

        subs_dict = {'targets' : " ".join(self.task.targets),
                     'dependencies': " ".join(self.task.file_dep)}
        # just included changed if it is set
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)
        # task option parameters
        subs_dict.update(self.task.options)
        return self.action % subs_dict

    def __str__(self):
        return "Cmd: %s" % self._action

    def __repr__(self):
        return "<CmdAction: '%s'>" % str(self._action)




class Writer(object):
    """write to many streams"""
    def __init__(self, *writers):
        """@param writers - file stream like objects"""
        self.writers = []
        self._isatty = True
        for writer in writers:
            self.add_writer(writer)

    def add_writer(self, stream, isatty=None):
        """adds a stream to the list of writers
        @param isatty: (bool) if specified overwrites real isatty from stream
        """
        self.writers.append(stream)
        isatty = stream.isatty() if (isatty is None) else isatty
        self._isatty = self._isatty and isatty

    def write(self, text):
        """write 'text' to all streams"""
        for stream in self.writers:
            stream.write(text)

    def flush(self):
        """flush all streams"""
        for stream in self.writers:
            stream.flush()

    def isatty(self):
        return self._isatty


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
        if inspect.isclass(self.py_callable):
            msg = "%r PythonAction can not be a class got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if inspect.isbuiltin(self.py_callable):
            msg = "%r PythonAction can not be a built-in got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if type(self.args) is not tuple and type(self.args) is not list:
            msg = "%r args must be a 'tuple' or a 'list'. got '%s'."
            raise InvalidTask(msg % (self.task, self.args))
        if type(self.kwargs) is not dict:
            msg = "%r kwargs must be a 'dict'. got '%s'"
            raise InvalidTask(msg % (self.task, self.kwargs))


    def _prepare_kwargs(self):
        return BaseAction._prepare_kwargs(self.task, self.py_callable,
                                          self.args, self.kwargs)

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
        output = StringIO()
        out_writer = Writer()
        # capture output but preserve isatty() from original stream
        out_writer.add_writer(output, old_stdout.isatty())
        if out:
            out_writer.add_writer(out)
        sys.stdout = out_writer

        old_stderr = sys.stderr
        errput = StringIO()
        err_writer = Writer()
        err_writer.add_writer(errput, old_stderr.isatty())
        if err:
            err_writer.add_writer(err)
        sys.stderr = err_writer

        kwargs = self._prepare_kwargs()

        # execute action / callable
        try:
            returned_value = self.py_callable(*self.args, **kwargs)
        except Exception as exception:
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
        elif isinstance(returned_value, six.string_types):
            self.result = returned_value
        elif isinstance(returned_value, dict):
            self.values = returned_value
            self.result = returned_value
        else:
            return TaskError("Python Task error: '%s'. It must return:\n"
                             "False for failed task.\n"
                             "True, None, string or dict for successful task\n"
                             "returned %s (%s)" %
                             (self.py_callable, returned_value,
                              type(returned_value)))

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

    if isinstance(action, six.string_types):
        return CmdAction(action, task_ref, shell=True)

    if isinstance(action, list):
        return CmdAction(action, task_ref, shell=False)

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
