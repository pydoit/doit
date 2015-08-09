import sys
import codecs
import six

from .exceptions import InvalidCommand
from .plugin import PluginDict
from .task import Task
from .control import TaskControl
from .runner import Runner, MRunner, MThreadRunner
from .cmd_base import DoitCmdBase
from . import reporter


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
    'type':str,
    'default': 'console',
    'help': """Choose output reporter.\n[default: %(default)s]"""
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


# use ".*" as default regex for delayed tasks without explicitly specified regex
opt_auto_delayed_regex = {
    'name': 'auto_delayed_regex',
    'short': '',
    'long': 'auto-delayed-regex',
    'type': bool,
    'default': False,
    'help':
"""Uses the default regex ".*" for every delayed task loader for which no regex was explicitly defined"""
}


class Run(DoitCmdBase):
    doc_purpose = "run tasks"
    doc_usage = "[TASK/TARGET...]"
    doc_description = None
    execute_tasks = True

    cmd_options = (opt_always, opt_continue, opt_verbosity,
                   opt_reporter, opt_outfile, opt_num_process,
                   opt_parallel_type, opt_pdb, opt_single,
                   opt_auto_delayed_regex)


    def __init__(self, **kwargs):
        super(Run, self).__init__(**kwargs)
        self.reporters = self.get_reporters() # dict


    def get_reporters(self):
        """return dict of all available reporters

        Also set CmdOption choices.
        """
        # built-in reporters
        reporters = {
            'console': reporter.ConsoleReporter,
            'executed-only': reporter.ExecutedOnlyReporter,
            'json': reporter.JsonReporter,
            'zero': reporter.ZeroReporter,
        }

        # plugins
        plugins = PluginDict()
        plugins.add_plugins(self.config, 'REPORTER')
        reporters.update(plugins.to_dict())

        # set choices for reporter cmdoption
        # sub-classes might not have this option
        if 'reporter' in self.cmdparser:
            choices = {k: v.desc for k,v in reporters.items()}
            self.cmdparser['reporter'].choices = choices

        return reporters


    def _execute(self, outfile,
                 verbosity=None, always=False, continue_=False,
                 reporter='console', num_process=0, par_type='process',
                 single=False, auto_delayed_regex=False):
        """
        @param reporter:
               (str) one of provided reporters or ...
               (class) user defined reporter class (can only be specified
                       from DOIT_CONFIG - never from command line)
               (reporter instance) - only used in unittests
        """
        # get tasks to be executed
        # self.control is saved on instance to be used by 'auto' command
        self.control = TaskControl(self.task_list,
                                   auto_delayed_regex=auto_delayed_regex)
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
            reporter_cls = self.reporters[reporter]
        else:
            # user defined class
            reporter_cls = reporter

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
        self.outstream = outstream

        # run
        try:
            # FIXME stderr will be shown twice in case of task error/failure
            if isinstance(reporter_cls, type):
                reporter_obj = reporter_cls(outstream, {'show_out': show_out,
                                                        'show_err': True})
            else:  # also accepts reporter instances
                reporter_obj = reporter_cls

            run_args = [self.dep_manager, reporter_obj,
                        continue_, always, verbosity]

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
