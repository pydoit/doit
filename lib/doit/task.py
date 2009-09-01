"""Task classes."""
from doit.action import create_action
from doit.exception import InvalidTask


# interface
class BaseTask(object):
    """Base class for all tasks objects

    @ivar name string
    @ivar action see derived classes
    @ivar dependencies list of all dependencies
    @ivar targets list of targets
    @ivar folder_dep: (list - string)
    @ivar task_dep: (list - string)
    @ivar file_dep: (list - string)
    @ivar run_once: (bool) task without dependencies should run
    @ivar is_subtask: (bool) indicate this task is a subtask.
    """

    def __init__(self,name,dependencies=(),targets=(),setup=None,
                 is_subtask=False):
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

        self.dependencies = dependencies
        self.targets = targets
        self.setup = setup
        self.run_once = False
        self.is_subtask = is_subtask

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
        raise Exception("Not Implemented")


    def title(self):
        """String representation on output.

        return: (string)
        """
        return "%s => %s"% (self.name,str(self))


class SingleActionTask(BaseTask):
    """
    Task that contains a single action
    """
    def __init__(self, name, action, dependencies=(), targets=(), setup=None,
                 is_subtask=False):
        """Init."""
        BaseTask.__init__(self, name, dependencies, targets, setup, is_subtask)

        self.action = create_action(action)


    def execute(self):
        """Executes the task.

        @raise TaskFailed:
        @raise TaskError:
        """
        self.action.execute()


    def __str__(self):
        return "\t%s" % self.action


class MultipleActionTask(BaseTask):
    """
    Task that contains multiple actions
    """
    def __init__(self, name, actions, dependencies=(), targets=(), setup=None,
                 is_subtask=False):
        """Init."""
        assert type(actions) is list, \
            "'action' from MultiAction must be a list."

        BaseTask.__init__(self, name, dependencies, targets, setup, is_subtask)

        self.actions = [create_action(a) for a in actions]


    def execute(self):
        """Executes the task.

        @raise TaskFailed:
        @raise TaskError:
        """
        for action in self.actions:
            action.execute()


    def __str__(self):
        return "\n\t".join([str(action) for action in self.actions])

            
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



def create_task(name,action,dependencies,targets,setup):
    """ create a BaseTask acording to action type

    @param name: (string) task name
    @param action: value dependes on the type of the task
    @param dependencies: (list of strings) each item is a file path or
    another task (prefixed with ':')
    @param targets: (list of strings) items are file paths.
    @param args: optional positional arguments for task.
    @param kwargs: optional keyword arguments for task.
    """
    if action is None:
        return GroupTask(name,dependencies,targets,setup)
    elif type(action) is list:
        return MultipleActionTask(name,action,dependencies,targets,setup)
    else:
        return SingleActionTask(name,action,dependencies,targets,setup)


def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict: (dict) task representation as a dict.
    @raise L{InvalidTask}:
    """
    # TASK_ATTRS: sequence of know attributes(keys) of a task dict.
    TASK_ATTRS = ('name','action','dependencies','targets','setup')
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
                       )

