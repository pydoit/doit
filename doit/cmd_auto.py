import sys
import itertools

from .control import TaskControl
from .filewatch import FileModifyWatcher
from .cmd_base import DoitCmdBase
from .cmd_run import opt_verbosity, Run


def _auto_watch(task_list, filter_tasks):
    """return list of tasks and files that need to be watched by auto cmd"""
    this_list = [t.clone() for t in task_list]
    task_control = TaskControl(this_list)
    task_control.process(filter_tasks)
    # remove duplicates preserving order
    task_set = set()
    tasks_to_run = []
    for dis in task_control.task_dispatcher(True):
        if dis.name not in task_set:
            tasks_to_run.append(dis)
            task_set.add(dis.name)
    watch_tasks = [t.name for t in tasks_to_run]
    watch_files = list(itertools.chain(*[s.file_dep for s in tasks_to_run]))
    watch_files = list(set(watch_files))
    return watch_tasks, watch_files



class Auto(DoitCmdBase):
    doc_purpose = "automatically execute tasks when a dependency changes"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_verbosity,)

    def _execute(self, verbosity=None, reporter='executed-only',
                 loop_callback=None):
        """Re-execute tasks automatically a depedency changes

        @param filter_tasks (list -str): print only tasks from this list
        @loop_callback: used to stop loop on unittests
        """
        watch_tasks, watch_files = _auto_watch(self.task_list, self.sel_tasks)
        auto_cmd = self
        class DoitAutoRun(FileModifyWatcher):
            """Execute doit on event handler of file changes """
            def handle_event(self, event):
                this_list = [t.clone() for t in auto_cmd.task_list]
                cmd_run = Run(dep_file=auto_cmd.dep_file, task_list=this_list,
                              sel_tasks=watch_tasks)
                cmd_run._execute(sys.stdout, verbosity=verbosity,
                                 reporter=reporter)

        file_watcher = DoitAutoRun(watch_files)
        # always run once when started
        file_watcher.handle_event(None)
        file_watcher.loop(loop_callback)

