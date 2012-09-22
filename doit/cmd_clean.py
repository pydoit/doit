
def doit_clean(task_list, outstream, dryrun, clean_dep, clean_all,
               default_tasks, selected_tasks):
    """Clean tasks
    @param task_list (list - L{Task}): list of all tasks from dodo file
    @ivar dryrun (bool): if True clean tasks are not executed
                        (just print out what would be executed)
    @param clean_dep (bool): execute clean from task_dep
    @param clean_all (bool): clean all tasks
    @param default_tasks (list - string): list of default tasks
    @param selected_tasks (list - string): list of tasks selected from cmd line
    """
    tasks = dict([(t.name, t) for t in task_list])
    cleaned = set()

    def clean_task(task_name):
        """wrapper to ensure task clean-action is executed only once"""
        if task_name not in cleaned:
            cleaned.add(task_name)
            tasks[task_name].clean(outstream, dryrun)

    # get list of tasks to be cleaned
    if clean_all:
        clean_list = [t.name for t in task_list]
    elif selected_tasks:
        clean_list = selected_tasks
    else:
        clean_list = default_tasks
        # if cleaning default tasks enable clean_dep automatically
        clean_dep = True

    for name in clean_list:
        # clean all task dependencies
        if clean_dep:
            for task_dep in tasks[name].task_dep:
                clean_task(task_dep)

        # clean only subtasks
        elif tasks[name].has_subtask:
            prefix = name + ':'
            for task_dep in tasks[name].task_dep:
                if task_dep.startswith(prefix):
                    clean_task(task_dep)
        clean_task(name)
