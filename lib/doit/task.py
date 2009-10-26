"""Task and actions classes."""
import subprocess, sys
import StringIO
import inspect
import os
from threading import Thread

from doit import TaskFailed, TaskError

# Exceptions
class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass




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

    def __init__(self, action):
        assert isinstance(action,str), "CmdAction must be a string."
        self.action = action
        self.task = None
        self.out = None
        self.err = None
        self.value = None

    def execute(self, out=None, err=None):
        """
        Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem

        @raise TaskError: If subprocess return code is greater than 125
        @raise TaskFailed: If subprocess return code isn't zero (and
        not greater than 125)
        """
        action = self.expand_action()

        # spawn task process
        process = subprocess.Popen(action, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def print_process_output(process, input, capture, realtime):
            while True:
                # line buffered
                line = input.readline()
                # unbuffered ? process.stdout.read(1)
                if line:
                    capture.write(line)
                    if realtime:
                        realtime.write(line)
                if process.poll() != None:
                    break

        output = StringIO.StringIO()
        errput = StringIO.StringIO()
        t_out = Thread(target=print_process_output,
                       args=(process, process.stdout, output, out))
        t_err = Thread(target=print_process_output,
                       args=(process, process.stderr, errput, err))
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        self.out = output.getvalue()
        self.err = errput.getvalue()
        self.value = self.out + self.err

        # task error - based on:
        # http://www.gnu.org/software/bash/manual/bashref.html#Exit-Status
        # it doesnt make so much difference to return as Error or Failed anyway
        if process.returncode > 125:
            raise TaskError("Command error: '%s' returned %s" %
                            (action,process.returncode))

        # task failure
        if process.returncode != 0:
            raise TaskFailed("Command failed: '%s' returned %s" %
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
        return self.action % subs_dict


    def __str__(self):
        return "Cmd: %s" % self.expand_action()

    def __repr__(self):
        return "<CmdAction: '%s'>"  % self.expand_action()




class Writer(object):
    """write to many streams"""
    def __init__(self, *writers) :
        self.writers = writers

    def write(self, text) :
        for w in self.writers :
                w.write(text)


class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar py_callable: (callable) Python callable that returns a boolean
    result depending on the success of the action
    @ivar args: (sequence)  Extra arguments to be passed to py_callable
    @ivar kwargs: (dict) Extra keyword arguments to be passed to py_callable
    @ivar task(Task): reference to task that contains this action
    """
    def __init__(self, py_callable, args=None, kwargs=None):

        self.py_callable = py_callable
        self.task = None
        self.out = None
        self.err = None
        self.value = None

        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

        # check valid parameters
        if not callable(self.py_callable):
            raise InvalidTask("PythonAction must be a 'callable'.")
        if type(self.args) is not tuple and type(self.args) is not list:
            msg = "args must be a 'tuple' or a 'list'. got '%s'."
            raise InvalidTask(msg % self.args)
        if type(self.kwargs) is not dict:
            msg = "kwargs must be a 'dict'. got '%s'"
            raise InvalidTask(msg % self.kwargs)


    def _prepare_kwargs(self):
        """
        Prepare keyword arguments (targets, dependencies, changed)
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

        @raise TaskFailed: If py_callable returns False
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
            # Python2.4
            try:
                result = self.py_callable(*self.args,**kwargs)
            # in python 2.4 SystemExit and KeyboardInterrupt subclass
            # from Exception.
            except (SystemExit, KeyboardInterrupt), exception:
                raise
            except Exception, exception:
                raise TaskError("PythonAction Error", exception)
        finally:
            # restore std streams /log captured streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.out = output.getvalue()
            self.err = errput.getvalue()

        self.value = result
        # if callable returns false. Task failed
        if result is False:
            raise TaskFailed("Python Task failed: '%s' returned %s" %
                             (self.py_callable, result))
        elif result is True or result is None or isinstance(result, str):
            return
        else:
            raise TaskError("Python Task error: '%s'. It must return:\n"
                            "False for failed task.\n"
                            "True, None or string for successful task\n"
                            "returned %s (%s)" %
                            (self.py_callable, result, type(result)))

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s"% str(self.py_callable)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonAction: '%s'>"% (repr(self.py_callable))


def create_action(action):
    """
    Create action using proper constructor based on the parameter type

    @param action: Action to be created
    @type action: L{BaseAction} subclass object, str, tuple or callable
    @raise InvalidTask: If action parameter type isn't valid
    """
    if isinstance(action, BaseAction):
        return action

    if type(action) is str:
        return CmdAction(action)

    if type(action) is tuple:
        return PythonAction(*action)

    if callable(action):
        return PythonAction(action)

    msg = "Invalid task action type. got %s"
    raise InvalidTask(msg % (action.__class__))




class Task(object):
    """Task

    @ivar name string
    @ivar actions: list - L{BaseAction}
    @ivar clean_actions: list - L{BaseAction}
    @ivar targets: (list -string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar dep_changed (list - string): list of file-dependencies that changed
          (are not up_to_date). this must be set before
    @ivar run_once: (bool) task without dependencies should run
    @ivar setup (list): List of setup objects
          (any object with setup or cleanup method)
    @ivar is_subtask: (bool) indicate this task is a subtask.
    @ivar doc: (string) task documentation
    """

    # list of valid types/values for each task attribute.
    valid_attr = {'name': [str],
                  'actions': [list, tuple, None],
                  'dependencies': [list, tuple],
                  'targets': [list, tuple],
                  'setup': [list, tuple],
                  'clean': [list, tuple, True],
                  'doc': [str, None]
                  }


    def __init__(self, name, actions, dependencies=(), targets=(),
                 setup=(), clean=(), is_subtask=False, doc=None):
        """sanity checks and initialization"""

        # check task attributes input
        for attr, valid_list in self.valid_attr.iteritems():
            self.check_attr_input(name, attr, locals()[attr], valid_list)

        self.name = name
        self.targets = targets
        self.setup = setup
        self.run_once = False
        self.is_subtask = is_subtask
        self.value = None

        if actions is None:
            self.actions = []
        else:
            self.actions = [create_action(a) for a in actions]

        if clean is True:
            self._remove_targets = True
            self.clean_actions = ()
        else:
            self._remove_targets = False
            self.clean_actions = [create_action(a) for a in clean]

        # set self as task for all actions
        for action in self.actions:
            action.task = self

        self.dep_changed = None
        # there are 2 kinds of dependencies: file, task
        self.task_dep = []
        self.file_dep = []
        self.result_dep = []
        for dep in dependencies:
            # True on the list. set run_once
            if isinstance(dep,bool):
                if not dep:
                    msg = ("%s. bool paramater in 'dependencies' "+
                           "must be True got:'%s'")
                    raise InvalidTask(msg%(name, str(dep)))
                self.run_once = True
            # task dep starts with a ':'
            elif dep.startswith(':'):
                self.task_dep.append(dep[1:])
            # task-result dep starts with a '?'
            elif dep.startswith('?'):
                self.result_dep.append(dep[1:])
            # file dep
            elif isinstance(dep,str):
                self.file_dep.append(dep)

        # run_once can't be used together with file dependencies
        if self.run_once and self.file_dep:
            msg = ("%s. task cant have file and dependencies and True " +
                   "at the same time. (just remove True)")
            raise InvalidTask(msg % name)

        # Store just first non-empty line as documentation string
        if doc is None:
            self.doc = ''
        else:
            for line in doc.splitlines():
                striped = line.strip()
                if striped:
                    self.doc = striped
                    break
            else:
                self.doc = ''


    @staticmethod
    def check_attr_input(task, attr, value, valid):
        """check input task attribute is correct type/value

        @param task (string): task name
        @param attr (string): attribute name
        @param value: actual input from user
        @param valid (list): of valid types/value accepted
        @raises InvalidTask if invalid input
        """
        msg = "Task %s attribute '%s' must be {%s} got:%r %s"
        for expected in valid:
            # check expected type
            if isinstance(expected, type):
                if isinstance(value, expected):
                    return
            # check expected value
            else:
                if expected is value:
                    return

        # input value didnt match any valid type/value, raise execption
        accept = ", ".join([getattr(v,'__name__',str(v)) for v in valid])
        raise InvalidTask(msg % (task, attr, accept, str(value), type(value)))


    def execute(self, out=None, err=None):
        """Executes the task.

        @raise TaskFailed: If raised when executing an action
        @raise TaskError: If raised when executing an action
        """
        for action in self.actions:
            action.execute(out, err)
            self.value = action.value


    def clean(self):
        """Execute task's clean"""
        # if clean is True remove all targets
        if self._remove_targets is True:
            files = filter(os.path.isfile, self.targets)
            dirs = filter(os.path.isdir, self.targets)

            # remove all files
            for file_ in files:
                os.remove(file_)

            # remove all directories (if empty)
            for dir_ in dirs:
                if os.listdir(dir_):
                    msg = "Warning: '%s' cannot be removed (it is not empty)\n"
                    sys.stderr.write(msg % dir_)
                else:
                    os.rmdir(dir_)

        else:
            # clean contains a list of actions...
            for action in self.clean_actions:
                action.execute()


    def title(self):
        """String representation on output.

        @rtype: str
        @return: Task name and actions
        """
        return "%s => %s"% (self.name, str(self))


    def __str__(self):
        if self.actions:
            return "\n\t".join([str(action) for action in self.actions])

        # A task that contains no actions at all
        # is used as group task
        return "Group: %s" % ", ".join(self.task_dep)

    def __repr__(self):
        return "<Task: %s>"% self.name


def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict (dict): task representation as a dict.
    @raise InvalidTask: If unexpected fields were passed in task_dict
    """
    # TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','actions','dependencies','targets','setup', 'doc',
                  'clean')
    # FIXME check field 'name'

    # check required fields
    if 'actions' not in task_dict:
        raise InvalidTask("Task %s must contain 'actions' field. %s" %
                          (task_dict['name'],task_dict))

    # user friendly. dont go ahead with invalid input.
    for key in task_dict.keys():
        if key not in TASK_ATTRS:
            raise InvalidTask("Task %s contain invalid field: %s"%
                              (task_dict['name'],key))

    return Task(**task_dict)
