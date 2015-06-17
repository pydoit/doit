"""starts a long-running process that whatches the file system and
automatically execute tasks when file dependencies change"""

import os
import time
import sys
from multiprocessing import Process
from subprocess import call

from .exceptions import InvalidCommand
from .cmdparse import CmdParse
from .filewatch import FileModifyWatcher
from .cmd_base import tasks_and_deps_iter
from .cmd_base import DoitCmdBase
from .cmd_run import opt_verbosity, Run

opt_reporter = {
    'name':'reporter',
    'short': None,
    'long': None,
    'type':str,
    'default': 'executed-only',
}

opt_success = {
    'name':'success_callback',
    'short': None,
    'long': 'success',
    'type':str,
    'default': '',
}

opt_failure = {
    'name':'failure_callback',
    'short': None,
    'long': 'failure',
    'type':str,
    'default': '',
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
    execute_tasks = True

    cmd_options = (opt_verbosity, opt_reporter, opt_success, opt_failure)

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


    @staticmethod
    def _run_callback(result, success_callback, failure_callback):
        '''run callback if any after task execution'''
        if result == 0:
            if success_callback:
                call(success_callback, shell=True)
        else:
            if failure_callback:
                call(failure_callback, shell=True)


    def run_watch(self, params, args):
        """Run tasks and wait for file system event

        This method is executed in a forked process.
        The process is terminated after a single event.
        """
        started = time.time()

        # execute tasks using Run Command
        arun = Run(task_loader=self.loader)
        params.add_defaults(CmdParse(arun.get_options()).parse([])[0])
        try:
            result = arun.execute(params, args)
        # ??? actually tested but coverage doesnt get it...
        except InvalidCommand as err: # pragma: no cover
            sys.stderr.write("ERROR: %s\n" % str(err))
            sys.exit(3)

        # user custom callbacks for result
        self._run_callback(result,
                           params.pop('success_callback', None),
                           params.pop('failure_callback', None))

        # get list of files to watch on file system
        watch_files = self._find_file_deps(arun.control.tasks,
                                           arun.control.selected_tasks)

        # Check for timestamp changes since run started,
        # if change, restart straight away
        if not self._dep_changed(watch_files, started, arun.control.targets):
            # set event handler. just terminate process.
            class DoitAutoRun(FileModifyWatcher):
                def handle_event(self, event):
                    # print("FS EVENT -> {}".format(event))
                    sys.exit(result)
            file_watcher = DoitAutoRun(watch_files)
            # kick start watching process
            file_watcher.loop()


    def execute(self, params, args):
        """loop executing tasks until process is interrupted"""
        while True:
            try:
                proc = Process(target=self.run_watch, args=(params, args))
                proc.start()
                proc.join()
                # if error on given command line, terminate.
                if proc.exitcode == 3:
                    return 3
            except KeyboardInterrupt:
                return 0
