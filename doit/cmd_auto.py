"""starts a long-running process that whatches the file system and
automatically execute tasks when file dependencies change"""

import os
import time
import sys
from multiprocessing import Process

from .cmdparse import CmdParse
from .filewatch import FileModifyWatcher
from .cmd_base import tasks_and_deps_iter
from .cmd_base import DoitCmdBase, check_tasks_exist
from .cmd_run import opt_verbosity, Run

opt_reporter = {'name':'reporter',
                 'short': None,
                 'long': None,
                 'type':str,
                 'default': 'executed-only',
                }


class Auto(DoitCmdBase):
    """the main process will never load tasks,
    delegates execution to a forked process.

    python caches imported modules,
    but using different process we can have dependencies on python
    modules making sure the newest module will be used.
    """

    doc_purpose = "automatically execute tasks when a dependency changes"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_verbosity, opt_reporter)

    @staticmethod
    def _find_file_deps(tasks, sel_tasks):
        """find all file deps
        @param tasks (dict)
        @param sel_tasks(list - str)
        """
        deps = set()
        for task in tasks_and_deps_iter(tasks, sel_tasks):
            deps.update(task.file_dep)
            deps.update(task.watch)
        return deps


    @staticmethod
    def _dep_changed(watch_files, started, targets):
        """check if watched files was modified since execution started"""
        for watched in watch_files:
            # assume that changes to targets were done by doit itself
            if watched in targets:
                continue
            if os.stat(watched).st_mtime > started:
                return True
        return False


    def run_watch(self, params, args):
        """Run tasks and wait for file system event

        This method is executed in a forked process.
        The process is terminated after a single event.
        """
        started = time.time()

        # execute tasks using Run Command
        ar = Run(task_loader=self._loader)
        params.add_defaults(CmdParse(ar.options).parse([])[0])
        result = ar.execute(params, args)

        # get list of files to watch on file system
        watch_files = self._find_file_deps(ar.control.tasks,
                                           ar.control.selected_tasks)

        # Check for timestamp changes since run started,
        # if change, restart straight away
        if not self._dep_changed(watch_files, started, ar.control.targets):
            # set event handler. just terminate process.
            class DoitAutoRun(FileModifyWatcher):
                def handle_event(self, event):
                    #print "FS EVENT -> ", event
                    sys.exit(result)
            file_watcher = DoitAutoRun(watch_files)
            # kick start watching process
            file_watcher.loop()


    def execute(self, params, args):
        """loop executing tasks until process is interrupted"""
        # check provided task names
        if args:
            task_list = self._loader.load_tasks(self, params, args)[0]
            tasks = dict([(t.name, t) for t in task_list])
            check_tasks_exist(tasks, args)

        while True:
            try:
                p = Process(target=self.run_watch, args=(params, args))
                p.start()
                p.join()
            except KeyboardInterrupt:
                return 0
