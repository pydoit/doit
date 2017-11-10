from .cmd_base import DoitCmdBase
from .cmd_base import check_tasks_exist, tasks_and_deps_iter, subtasks_iter


opt_clean_dryrun = {
    'name': 'dryrun',
    'short': 'n', # like make dry-run
    'long': 'dry-run',
    'type': bool,
    'default': False,
    'help': 'print actions without really executing them',
    }

opt_clean_cleandep = {
    'name': 'cleandep',
    'short': 'c', # clean
    'long': 'clean-dep',
    'type': bool,
    'default': False,
    'help': 'clean task dependencies too',
    }

opt_clean_cleanall = {
    'name': 'cleanall',
    'short': 'a', # all
    'long': 'clean-all',
    'type': bool,
    'default': False,
    'help': 'clean all task',
    }

opt_clean_forget = {
    'name': 'cleanforget',
    'long': 'forget',
    'type': bool,
    'default': False,
    'help': 'also forget tasks after cleaning',
    }

class Clean(DoitCmdBase):
    doc_purpose = "clean action / remove targets"
    doc_usage = "[TASK ...]"
    doc_description = ("If no task is specified clean default tasks and "
                       "set --clean-dep automatically.")

    cmd_options = (opt_clean_cleandep, opt_clean_cleanall, opt_clean_dryrun, opt_clean_forget)


    def clean_tasks(self, tasks, dryrun, cleanforget):
        """ensure task clean-action is executed only once"""
        cleaned = set()
        forget_tasks = cleanforget and not dryrun
        for task in tasks:
            if task.name not in cleaned:
                cleaned.add(task.name)
                task.clean(self.outstream, dryrun)
                if forget_tasks:
                    self.dep_manager.remove(task.name)

        self.dep_manager.close()

    def _execute(self, dryrun, cleandep, cleanall, cleanforget, pos_args=None):
        """Clean tasks
        @param task_list (list - L{Task}): list of all tasks from dodo file
        @ivar dryrun (bool): if True clean tasks are not executed
                            (just print out what would be executed)
        @param cleandep (bool): execute clean from task_dep
        @param cleanall (bool): clean all tasks
        @param cleanforget (bool): forget cleaned tasks
        @var default_tasks (list - string): list of default tasks
        @var selected_tasks (list - string): list of tasks selected
                                             from cmd-line
        """
        tasks = dict([(t.name, t) for t in self.task_list])
        # behavior of cleandep is different if selected_tasks comes from
        # command line or DOIT_CONFIG.default_tasks
        selected_tasks = pos_args
        check_tasks_exist(tasks, selected_tasks)

        # get base list of tasks to be cleaned
        if cleanall:
            clean_list = [t.name for t in self.task_list]
        elif selected_tasks:
            clean_list = selected_tasks
        else:
            if self.sel_tasks is None:
                clean_list = [t.name for t in self.task_list]
            else:
                clean_list = self.sel_tasks
            # if cleaning default tasks enable clean_dep automatically
            cleandep = True

        # include dependencies in list
        if cleandep:
            # including repeated entries will guarantee that deps are listed
            # first when the list is reversed
            to_clean = list(tasks_and_deps_iter(tasks, clean_list, True))
        # include only subtasks in list
        else:
            to_clean = []
            for name in reversed(clean_list):
                task = tasks[name]
                to_clean.append(task)
                to_clean.extend(subtasks_iter(tasks, task))
        to_clean.reverse()
        self.clean_tasks(to_clean, dryrun, cleanforget)
