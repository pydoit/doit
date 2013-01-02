"""starts a long-running process that whatches the file system and
automatically execute tasks when file dependencies change"""

import os
import sys
import itertools

from .cmdparse import CmdParse
from .filewatch import FileModifyWatcher
from .cmd_base import DoitCmdBase
from .cmd_run import opt_verbosity, Run

opt_reporter = {'name':'reporter',
                 'short': None,
                 'long': None,
                 'type':str,
                 'default': 'executed-only',
                }


class Auto(DoitCmdBase):
    doc_purpose = "automatically execute tasks when a dependency changes"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_verbosity, opt_reporter)

    def run_watch(self, params, args):
        """run tasks and wait for file system event
        to be executed in a forked process
        """
        # execute tasks using Run Command
        ar = Run(task_loader=self._loader, dep_file=self.dep_file)
        for key, value in (CmdParse(ar.options).parse([])[0]).iteritems():
            if key not in params._non_default_keys:
                params.set_default(key, value)
        result = ar.execute(params, args)

        # get list of files to watch on file system
        # FIXME get real list of files
        watch_files = list(itertools.chain(*[t.file_dep for t in ar.task_list]))

        # set event handler. just terminate process
        class DoitAutoRun(FileModifyWatcher):
            def handle_event(self, event):
                print "FS EVENT -> ", event
                sys.exit(result)
        file_watcher = DoitAutoRun(watch_files)


        # FIXME events while tasks are running gonna be lost.
        # Check for timestamp changes since run started,
        # if no change: watch & wait
        # else: restart straight away

        # kick start watching process
        file_watcher.loop()


    def execute(self, params, args):
        """the main process will never load tasks,
        delegates execution to a forked process.

        python caches imported modules,
        but using different process we can have dependencies on python
        modules making sure the newest module will be used.
        """
        child_pid = os.fork()
        if child_pid:
            # child process will execute tasks and wait for file system event
            # after event child is terminated...
            os.waitpid(child_pid, 0)
            # ... repeat process, fork again.
            self.execute(params, args)
        else:
            self.run_watch(params, args)
