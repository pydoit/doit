from .cmd_base import DoitCmdBase, check_tasks_exist
from .cmd_base import subtasks_iter


class ResetDep(DoitCmdBase):
    name = "reset-dep"
    doc_purpose = "recompute the state of file dependencies"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = ()

    def _execute(self, pos_args=None):
        filter_tasks = pos_args

        # dict of all tasks
        tasks = dict([(t.name, t) for t in self.task_list])

        if filter_tasks:
            # list only tasks passed on command line
            check_tasks_exist(tasks, filter_tasks)
            # get task by name
            task_list = []
            for name in filter_tasks:
                task = tasks[name]
                task_list.append(task)
                task_list.extend(subtasks_iter(tasks, task))
        else:
            task_list = self.task_list

        write = self.outstream.write
        for task in task_list:
            # Save this now because dep_manager.get_status will remove the task
            # from the db if the checker changed.
            task.values = self.dep_manager.get_values(task.name)
            task.results = self.dep_manager.get_results(task.name)

            try:
                run_status = self.dep_manager.get_status(task, tasks)
            except Exception:
                run_status = 'run'

            if run_status == 'up-to-date':
                write("skip %s\n" % task.name)
                continue

            try:
                self.dep_manager.save_success(task)
            except OSError:
                write("skip (missing file_dep) %s\n" % task.name)
            else:
                write("processed %s\n" % task.name)

        self.dep_manager.close()
