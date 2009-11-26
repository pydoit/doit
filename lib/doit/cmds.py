"""cmd-line functions"""
import sys

from doit import dependency
from doit.task import Task
from doit.main import TaskSetup, InvalidCommand
from doit.runner import run_tasks
from doit.reporter import REPORTERS


def doit_run(dependencyFile, task_list, options=None,
             verbosity=None, alwaysExecute=False, continue_=False,
             reporter='default', outfile=None):
    # get tasks to be executed
    selected_tasks = TaskSetup(task_list, options).process()

    if reporter not in REPORTERS:
        msg = ("No reporter named '%s'.\nType 'doit help run' to see a list "
               "of available reporters.")
        raise InvalidCommand(msg % reporter)
    reporter_cls = REPORTERS[reporter]

    if verbosity is None:
        use_verbosity = Task.DEFAULT_VERBOSITY
    else:
        use_verbosity = verbosity
    show_out = use_verbosity < 2 # show on error report

    if outfile is None:
        outstream = sys.stdout
    else:
        outstream = open(outfile, 'w')
    try:
        # FIXME stderr will be shown twice in case of task error/failure
        reporter_obj = reporter_cls(outstream, show_out , True)

        return run_tasks(dependencyFile, selected_tasks, reporter_obj,
                         verbosity, alwaysExecute, continue_)
    finally:
        if outfile is not None:
            outstream.close()



def doit_clean(task_list, outstream, clean_tasks):
    """Clean tasks
    @param task_list (list - L{Task}): list of all tasks from dodo file
    @param clean_tasks (list - string): tasks bo be clean. clean all if
                                        empty list.
    """
    if not clean_tasks:
        for task_ in task_list:
            task_.clean()
    else:
        tasks = dict([(t.name, t) for t in task_list])
        for name in clean_tasks:
            tasks[name].clean()


def doit_list(task_list, outstream, printSubtasks, quiet=False):
    """List task generators, in the order they were defined.

    @param printSubtasks: (bool) print subtasks
    @param outstream: (file-like) object
    """
    for task in task_list:
        if (not task.is_subtask) or printSubtasks:
            task_str = task.name
            if not quiet and task.doc:
                task_str += " : %s" % task.doc
            outstream.write("%s\n" % task_str)
    return 0


def doit_forget(dbFileName, taskList, outstream, forgetTasks):
    """remove saved data successful runs from DB
    @param dbFileName: (str)
    @param task_list: (Task) tasks from dodo file
    @param forget_tasks: (list - str) tasks to be removed. remove all if
                         empty list.
    """
    dependencyManager = dependency.Dependency(dbFileName)
    # no task specified. forget all
    if not forgetTasks:
        dependencyManager.remove_all()
        outstream.write("forgeting all tasks\n")
    # forget tasks from list
    else:
        tasks = dict([(t.name, t) for t in taskList])
        for taskName in forgetTasks:
            # check task exist
            if taskName not in tasks:
                msg = "'%s' is not a task."
                raise InvalidCommand(msg % taskName)
            # for group tasks also remove all tasks from group.
            group = [taskName]
            while group:
                to_forget = group.pop(0)
                if not tasks[to_forget].actions:
                    # get task dependencies only from group-task
                    group.extend(tasks[to_forget].task_dep)
                # forget it - remove from dependency file
                dependencyManager.remove(to_forget)
                outstream.write("forgeting %s\n" % to_forget)
    dependencyManager.close()


def doit_ignore(dbFileName, taskList, outstream, ignoreTasks):
    """mark tasks to be ignored
    @param dbFileName: (str)
    @param taskList: (Task) tasks from dodo file
    @param ignoreTasks: (list - str) tasks to be ignored.
    """
    # no task specified.
    if not ignoreTasks:
        outstream.write("You cant ignore all tasks! Please select a task.\n")
        return

    dependencyManager = dependency.Dependency(dbFileName)
    tasks = dict([(t.name, t) for t in taskList])
    for taskName in ignoreTasks:
        # check task exist
        if taskName not in tasks:
            msg = "'%s' is not a task."
            raise InvalidCommand(msg % taskName)
        # for group tasks also remove all tasks from group.
        # FIXME: DRY
        group = [taskName]
        while group:
            to_ignore = group.pop(0)
            if not tasks[to_ignore].actions:
                # get task dependencies only from group-task
                group.extend(tasks[to_ignore].task_dep)
            # ignore it - remove from dependency file
            dependencyManager.ignore(tasks[to_ignore])
            outstream.write("ignoring %s\n" % to_ignore)
    dependencyManager.close()
