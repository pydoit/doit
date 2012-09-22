from . import dependency
from .exceptions import InvalidCommand


def doit_forget(dependency_file, task_list, outstream, forget_tasks):
    """remove saved data successful runs from DB
    @param dependency_file: (str)
    @param task_list: (Task) tasks from dodo file
    @param forget_tasks: (list - str) tasks to be removed. remove all if
                         empty list.
    """
    dependency_manager = dependency.Dependency(dependency_file)
    # no task specified. forget all
    if not forget_tasks:
        dependency_manager.remove_all()
        outstream.write("forgeting all tasks\n")
    # forget tasks from list
    else:
        tasks = dict([(t.name, t) for t in task_list])
        for task_name in forget_tasks:
            # check task exist
            if task_name not in tasks:
                msg = "'%s' is not a task."
                raise InvalidCommand(msg % task_name)
            # for group tasks also remove all tasks from group.
            group = [task_name]
            while group:
                to_forget = group.pop(0)
                if not tasks[to_forget].actions:
                    # get task dependencies only from group-task
                    group.extend(tasks[to_forget].task_dep)
                # forget it - remove from dependency file
                dependency_manager.remove(to_forget)
                outstream.write("forgeting %s\n" % to_forget)
    dependency_manager.close()
