from .exceptions import InvalidCommand
from .cmd_base import DoitCmdBase

opt_clean_dryrun = {'name': 'dryrun',
                    'short': 'n', # like make dry-run
                    'long': 'dry-run',
                    'type': bool,
                    'default': False,
                    'help': 'print actions without really executing them'}

opt_clean_cleandep = {'name': 'cleandep',
                    'short': 'c', # clean
                    'long': 'clean-dep',
                    'type': bool,
                    'default': False,
                    'help': 'clean task dependencies too'}

opt_clean_cleanall = {
    'name': 'cleanall',
    'short': 'a', # clean
    'long': 'clean-all',
    'type': bool,
    'default': False,
    'help': 'clean all task'}


class Clean(DoitCmdBase):
    doc_purpose = "clean action / remove targets"
    doc_usage = "[TASK ...]"
    doc_description = ("If no task is specified clean default tasks and "
                       "set --clean-dep automatically.")

    cmd_options = (opt_clean_cleandep, opt_clean_cleanall, opt_clean_dryrun)


    def _execute(self, dryrun, cleandep, cleanall, pos_args=None):
        """Clean tasks
        @param task_list (list - L{Task}): list of all tasks from dodo file
        @ivar dryrun (bool): if True clean tasks are not executed
                            (just print out what would be executed)
        @param cleandep (bool): execute clean from task_dep
        @param cleanall (bool): clean all tasks
        @var default_tasks (list - string): list of default tasks
        @var selected_tasks (list - string): list of tasks selected from cmd line
        """
        tasks = dict([(t.name, t) for t in self.task_list])
        default_tasks = self.config.get('default_tasks')
        selected_tasks = pos_args
        cleaned = set()

        # check task exist
        if selected_tasks:
            for task_name in selected_tasks:
                if task_name not in tasks:
                    msg = "'%s' is not a task."
                    raise InvalidCommand(msg % task_name)


        def clean_task(task_name):
            """wrapper to ensure task clean-action is executed only once"""
            if task_name not in cleaned:
                cleaned.add(task_name)
                tasks[task_name].clean(self.outstream, dryrun)

        # get list of tasks to be cleaned
        if cleanall:
            clean_list = [t.name for t in self.task_list]
        elif selected_tasks:
            clean_list = selected_tasks
        else:
            clean_list = default_tasks
            # if cleaning default tasks enable clean_dep automatically
            cleandep = True

        for name in clean_list:
            # clean all task dependencies
            if cleandep:
                for task_dep in tasks[name].task_dep:
                    clean_task(task_dep)

            # clean only subtasks
            elif tasks[name].has_subtask:
                prefix = name + ':'
                for task_dep in tasks[name].task_dep:
                    if task_dep.startswith(prefix):
                        clean_task(task_dep)
            clean_task(name)
