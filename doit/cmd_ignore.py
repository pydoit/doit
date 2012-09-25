from . import dependency
from .exceptions import InvalidCommand
from .cmd_base import DoitCmdBase


class Ignore(DoitCmdBase):
    doc_purpose = "ignore task (skip) on subsequent runs"
    doc_usage = "TASK [TASK ...]"
    doc_description = None

    cmd_options = ()

    def _execute(self, pos_args):
        """mark tasks to be ignored
        @param ignore_tasks: (list - str) tasks to be ignored.
        """
        ignore_tasks = pos_args
        # no task specified.
        if not ignore_tasks:
            msg = "You cant ignore all tasks! Please select a task.\n"
            self.outstream.write(msg)
            return

        dependency_manager = dependency.Dependency(self.dep_file)
        tasks = dict([(t.name, t) for t in self.task_list])
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
                self.outstream.write("ignoring %s\n" % to_ignore)
        dependency_manager.close()
