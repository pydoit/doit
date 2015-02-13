import sys
import codecs
import six

from .exceptions import InvalidCommand
from .task import Task
from .control import TaskControl
from .runner import Runner, MRunner, MThreadRunner
from .reporter import REPORTERS
from .cmd_base import DoitCmdBase
from .dependency import CHECKERS


# verbosity
opt_verbosity = {
    'name':'verbosity',
    'short':'v',
    'long':'verbosity',
    'type':int,
    'default': None,
    'help': """0 capture (do not print) stdout/stderr from task.
1 capture stdout only.
2 do not capture anything (print everything immediately).
[default: 1]"""
}


# select output file
opt_outfile = {
    'name': 'outfile',
    'short':'o',
    'long': 'output-file',
    'type': str,
    'default': sys.stdout,
    'help':"write output into file [default: stdout]"
}


# always execute task
opt_always = {
    'name': 'always',
    'short': 'a',
    'long': 'always-execute',
    'type': bool,
    'default': False,
    'help': "always execute tasks even if up-to-date [default: %(default)s]",
}

# continue executing tasks even after a failure
opt_continue = {
    'name': 'continue',
    'short': 'c',
    'long': 'continue',
    'inverse': 'no-continue',
    'type': bool,
    'default': False,
    'help': ("continue executing tasks even after a failure " +
             "[default: %(default)s]"),
}


opt_single = {
    'name': 'single',
    'short': 's',
    'long': 'single',
    'type': bool,
    'default': False,
    'help': ("Execute only specified tasks ignoring their task_dep " +
             "[default: %(default)s]"),
}


opt_num_process = {
    'name': 'num_process',
    'short': 'n',
    'long': 'process',
    'type': int,
    'default': 0,
    'help': "number of subprocesses [default: %(default)s]"
}


# reporter
opt_reporter = {
    'name':'reporter',
    'short':'r',
    'long':'reporter',
    'type':str, #TODO type choice (limit the accepted strings)
    'default': 'default',
    'help': """Choose output reporter. Available:
'default': report output on console
'executed-only': no output for skipped (up-to-date) and group tasks
'json': output result in json format
[default: %(default)s]
"""
}

opt_check_file_uptodate = {
    'name': 'check_file_uptodate',
    'short': '',
    'long': 'check_file_uptodate',
    'type': str,
    'default': 'md5',
    'help': """\
Choose how to check if files have been modified. Available:
'md5': use the md5sum
'timestamp': use the timestamp
"""
}

opt_parallel_type = {
    'name':'par_type',
    'short':'P',
    'long':'parallel-type',
    'type':str,
    'default': 'process',
    'help': """Tasks can be executed in parallel in different ways:
'process': uses python multiprocessing module
'thread': uses threads
[default: %(default)s]
"""
}


# pdb post-mortem
opt_pdb = {
    'name':'pdb',
    'short':'',
    'long':'pdb',
    'type': bool,
    'default': None,
    'help':
"""get into PDB (python debugger) post-mortem in case of unhandled exception"""
    }


class Run(DoitCmdBase):
    doc_purpose = "run tasks"
    doc_usage = "[TASK/TARGET...]"
    doc_description = None
    execute_tasks = True

    cmd_options = (opt_always, opt_continue, opt_verbosity,
                   opt_reporter, opt_outfile, opt_num_process,
                   opt_parallel_type, opt_pdb, opt_single,
                   opt_check_file_uptodate)

    def _execute(self, outfile,
                 verbosity=None, always=False, continue_=False,
                 reporter='default', num_process=0, par_type='process',
                 single=False, check_file_uptodate='md5'):
        """
        @param reporter:
               (str) one of provided reporters or ...
               (class) user defined reporter class (can only be specified
                       from DOIT_CONFIG - never from command line)
               (reporter instance) - only used in unittests
        """
        # get tasks to be executed
        # self.control is saved on instance to be used by 'auto' command
        self.control = TaskControl(self.task_list)
        self.control.process(self.sel_tasks)

        if single:
            for task_name in self.sel_tasks:
                task = self.control.tasks[task_name]
                if task.has_subtask:
                    for task_name in task.task_dep:
                        sub_task = self.control.tasks[task_name]
                        sub_task.task_dep = []
                else:
                    task.task_dep = []

        # reporter
        if isinstance(reporter, six.string_types):
            if reporter not in REPORTERS:
                msg = ("No reporter named '{}'."
                       " Type 'doit help run' to see a list "
                       "of available reporters.")
                raise InvalidCommand(msg.format(reporter))
            reporter_cls = REPORTERS[reporter]
        else:
            # user defined class
            reporter_cls = reporter

        # check_file_uptodate
        if isinstance(check_file_uptodate, six.string_types):
            if check_file_uptodate not in CHECKERS:
                msg = ("No check_file_uptodate named '{}'."
                       " Type 'doit help run' to see a list "
                       "of available checkers.")
                raise InvalidCommand(msg.format(check_file_uptodate))
            checker_cls = CHECKERS[check_file_uptodate]
        else:
            # user defined class
            checker_cls = check_file_uptodate

        # verbosity
        if verbosity is None:
            use_verbosity = Task.DEFAULT_VERBOSITY
        else:
            use_verbosity = verbosity
        show_out = use_verbosity < 2  # show on error report

        # outstream
        if isinstance(outfile, six.string_types):
            outstream = codecs.open(outfile, 'w', encoding='utf-8')
        else:  # outfile is a file-like object (like StringIO or sys.stdout)
            outstream = outfile

        # run
        try:
            # FIXME stderr will be shown twice in case of task error/failure
            if isinstance(reporter_cls, type):
                reporter_obj = reporter_cls(outstream, {'show_out': show_out,
                                                        'show_err': True})
            else:  # also accepts reporter instances
                reporter_obj = reporter_cls

            run_args = [self.dep_class, self.dep_file, reporter_obj,
                        checker_cls, continue_, always, verbosity]

            if num_process == 0:
                RunnerClass = Runner
            else:
                if par_type == 'process':
                    RunnerClass = MRunner
                    if not MRunner.available():
                        RunnerClass = MThreadRunner
                        sys.stderr.write(
                            "WARNING: multiprocessing module not available, " +
                            "running in parallel using threads.")
                elif par_type == 'thread':
                    RunnerClass = MThreadRunner
                else:
                    msg = "Invalid parallel type %s"
                    raise InvalidCommand(msg % par_type)
                run_args.append(num_process)

            runner = RunnerClass(*run_args)
            return runner.run_all(self.control.task_dispatcher())
        finally:
            if isinstance(outfile, str):
                outstream.close()
