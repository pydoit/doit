from . import dependency
from .exceptions import InvalidCommand


def doit_ignore(dependency_file, task_list, outstream, ignore_tasks):
    """mark tasks to be ignored
    @param dependency_file: (str)
    @param task_list: (Task) tasks from dodo file
    @param ignore_tasks: (list - str) tasks to be ignored.
    """
    # no task specified.
    if not ignore_tasks:
        outstream.write("You cant ignore all tasks! Please select a task.\n")
        return

    dependency_manager = dependency.Dependency(dependency_file)
    tasks = dict([(t.name, t) for t in task_list])
    for task_name in ignore_tasks:
        # check task exist
        if task_name not in tasks:
            msg = "'%s' is not a task."
            raise InvalidCommand(msg % task_name)
        # for group tasks also remove all tasks from group.
        # FIXME: DRY
        group = [task_name]
        while group:
            to_ignore = group.pop(0)
            if not tasks[to_ignore].actions:
                # get task dependencies only from group-task
                group.extend(tasks[to_ignore].task_dep)
            # ignore it - remove from dependency file
            dependency_manager.ignore(tasks[to_ignore])
            outstream.write("ignoring %s\n" % to_ignore)
    dependency_manager.close()
