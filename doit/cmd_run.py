import sys
import codecs

from .exceptions import InvalidCommand
from .plugin import PluginDict
from .action import PythonAction
from .task import Stream
from .control import TaskControl
from .runner import Runner, MThreadRunner
from .cmd_base import DoitCmdBase
from .cmdparse import CmdOption
from . import reporter


# Run command options as dataclasses with documented short flags.
# Each short option letter is documented in a comment explaining its meaning.

opt_verbosity = CmdOption(
    name='verbosity',
    default=None,
    type=int,
    short='v',   # v for verbosity level
    long='verbosity',
    help="""0 capture (do not print) stdout/stderr from task.
1 capture stdout only.
2 do not capture anything (print everything immediately).
[default: 1]""",
)

opt_outfile = CmdOption(
    name='outfile',
    default=sys.stdout,
    type=str,
    short='o',   # o for output file
    long='output-file',
    help="write output into file [default: stdout]",
)

opt_always = CmdOption(
    name='always',
    default=False,
    type=bool,
    short='a',   # a for always execute
    long='always-execute',
    help="always execute tasks even if up-to-date [default: %(default)s]",
)

opt_continue = CmdOption(
    name='continue',
    default=False,
    type=bool,
    short='c',   # c for continue on failure
    long='continue',
    inverse='no-continue',
    help="continue executing tasks even after a failure [default: %(default)s]",
)

opt_single = CmdOption(
    name='single',
    default=False,
    type=bool,
    short='s',   # s for single (ignore task_dep)
    long='single',
    help="Execute only specified tasks ignoring their task_dep [default: %(default)s]",
)

opt_num_process = CmdOption(
    name='num_process',
    default=0,
    type=int,
    short='n',   # n for number of threads
    long='process',
    help="number of parallel threads [default: %(default)s]",
)

opt_reporter = CmdOption(
    name='reporter',
    default='console',
    type=str,
    short='r',   # r for reporter
    long='reporter',
    help="Choose output reporter. [default: %(default)s]",
)

opt_pdb = CmdOption(
    name='pdb',
    default=None,
    type=bool,
    short='',    # no short option
    long='pdb',
    help="get into PDB (python debugger) post-mortem in case of unhandled exception",
)

opt_auto_delayed_regex = CmdOption(
    name='auto_delayed_regex',
    default=False,
    type=bool,
    short='',    # no short option
    long='auto-delayed-regex',
    help='Uses the default regex ".*" for every delayed task loader for which no regex was explicitly defined',
)

opt_report_failure_verbosity = CmdOption(
    name='failure_verbosity',
    default=0,
    type=int,
    short='',    # no short option
    long='failure-verbosity',
    help="""Control re-display stdout/stderr for failed tasks on report summary.
0 do not show re-display
1 re-display stderr only
2 re-display both stderr/stdout
[default: 0]""",
)


class Run(DoitCmdBase):
    doc_purpose = "run tasks"
    doc_usage = "[TASK/TARGET...]"
    doc_description = None
    execute_tasks = True

    cmd_options = (opt_always, opt_continue, opt_verbosity,
                   opt_reporter, opt_outfile, opt_num_process,
                   opt_pdb, opt_single,
                   opt_auto_delayed_regex, opt_report_failure_verbosity)


    def __init__(self, **kwargs):
        super(Run, self).__init__(**kwargs)
        self.reporters = self.get_reporters()  # dict


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
            'error-only': reporter.ErrorOnlyReporter,
        }

        # plugins
        plugins = PluginDict()
        plugins.add_plugins(self.config, 'REPORTER')
        reporters.update(plugins.to_dict())

        # set choices for reporter cmdoption
        # sub-classes might not have this option
        if 'reporter' in self.cmdparser:
            choices = {k: v.desc for k, v in reporters.items()}
            self.cmdparser['reporter'].choices = choices

        return reporters


    def _execute(self, outfile,
                 verbosity=None, always=False, continue_=False,
                 reporter='console', num_process=0,
                 single=False, auto_delayed_regex=False, force_verbosity=False,
                 failure_verbosity=0, pdb=False):
        """
        @param reporter:
               (str) one of provided reporters or ...
               (class) user defined reporter class (can only be specified
                       from DOIT_CONFIG - never from command line)
               (reporter instance) - only used in unittests
        """
        # configure PythonAction
        PythonAction.pm_pdb = pdb

        # get tasks to be executed
        # self.control is saved on instance to be used by 'auto' command
        self.control = TaskControl(self.task_list,
                                   auto_delayed_regex=auto_delayed_regex)
        self.control.process(self.sel_tasks)

        if single:
            self.control.process(self.sel_tasks)
            for task_name in self.control.selected_tasks:
                task = self.control.tasks[task_name]
                if task.has_subtask:
                    for task_name in task.task_dep:
                        sub_task = self.control.tasks[task_name]
                        sub_task.task_dep = []
                else:
                    task.task_dep = []

        # reporter
        if isinstance(reporter, str):
            reporter_cls = self.reporters[reporter]
        else:
            # user defined class
            reporter_cls = reporter

        # outstream
        if isinstance(outfile, str):
            outstream = codecs.open(outfile, 'w', encoding='utf-8')
        else:  # outfile is a file-like object (like StringIO or sys.stdout)
            outstream = outfile
        self.outstream = outstream

        # run
        try:
            if isinstance(reporter_cls, type):
                reporter_obj = reporter_cls(
                    outstream, {'failure_verbosity': failure_verbosity})
            else:  # also accepts reporter instances
                reporter_obj = reporter_cls

            stream = Stream(verbosity, force_verbosity)
            run_args = [self.dep_manager, reporter_obj,
                        continue_, always, stream]

            if num_process == 0:
                RunnerClass = Runner
            else:
                RunnerClass = MThreadRunner
                run_args.append(num_process)

            runner = RunnerClass(*run_args)
            return runner.run_all(self.control)
        finally:
            if isinstance(outfile, str):
                outstream.close()
