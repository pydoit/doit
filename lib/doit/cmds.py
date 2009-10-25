"""cmd-line functions"""
import sys

from doit import dependency
from doit.main import TaskSetup, InvalidCommand
from doit.runner import run_tasks
from doit.reporter import REPORTERS


VERBOSITY = [(None, None), # None => capture
             (None, sys.stderr),
             (sys.stdout, sys.stderr)] # use parent process
"""map verbosity to control capture of tasks' stdout and stderr
 - 0 => print (stderr and stdout) from failed tasks
 - 1 => print stderr and (stdout from failed tasks)
 - 2 => print stderr and stdout from all tasks
"""

def doit_run(dependencyFile, task_list, filter_=None,
             verbosity=0, alwaysExecute=False, continue_=False,
             reporter='default'):
    # get tasks to be executed
    selected_tasks = TaskSetup(task_list, filter_).process()
    task_stdout, task_stderr = VERBOSITY[verbosity]

    if reporter not in REPORTERS:
        msg = ("No reporter named '%s'.\nType 'doit help run' to see a list "
               "of available reporters.")
        raise InvalidCommand(msg % reporter)
    reporter_cls = REPORTERS[reporter]
    reporter_obj = reporter_cls(task_stdout is None, task_stderr is None)

    return run_tasks(dependencyFile, selected_tasks, reporter_obj,
                     task_stdout, task_stderr, alwaysExecute, continue_)


def doit_clean(task_list, clean_tasks):
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


def doit_list(task_list, printSubtasks, quiet=False):
    """List task generators, in the order they were defined.

    @param printSubtasks: (bool) print subtasks
    """
    for task in task_list:
        if (not task.is_subtask) or printSubtasks:
            task_str = task.name
            if not quiet and task.doc:
                task_str += " : %s" % task.doc
            print task_str
    return 0


def doit_forget(dbFileName, taskList, forgetTasks):
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
        print "forgeting all tasks"
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
                print "forgeting %s" % to_forget
    dependencyManager.close()
