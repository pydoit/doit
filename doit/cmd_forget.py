from . import dependency
from .exceptions import InvalidCommand
from .cmd_base import DoitCmdBase


class Forget(DoitCmdBase):
    doc_purpose = "clear successful run status from internal DB"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = ()

    def _execute(self):
        """remove saved data successful runs from DB
        """
        dependency_manager = dependency.Dependency(self.dep_file)
        # no task specified. forget all
        if not self.sel_tasks:
            dependency_manager.remove_all()
            self.outstream.write("forgeting all tasks\n")
        # forget tasks from list
        else:
            tasks = dict([(t.name, t) for t in self.task_list])
            for task_name in self.sel_tasks:
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
                    self.outstream.write("forgeting %s\n" % to_forget)
        dependency_manager.close()
