import sys
import codecs

from .exceptions import InvalidCommand
from .task import Task
from .control import TaskControl
from .runner import Runner, MRunner
from .reporter import REPORTERS


def doit_run(dependency_file, task_list, output, options=None,
             verbosity=None, always_execute=False, continue_=False,
             reporter='default', num_process=0):
    """
    @param reporter: (str) one of provided reporters or ...
                     (class) user defined reporter class (can only be specified
           from DOIT_CONFIG - never from command line)
                     (reporter instance) - only used in unittests
    """
    # get tasks to be executed
    task_control = TaskControl(task_list)
    task_control.process(options)

    # reporter
    if isinstance(reporter, basestring):
        if reporter not in REPORTERS:
            msg = ("No reporter named '%s'."
                   " Type 'doit help run' to see a list "
                   "of available reporters.")
            raise InvalidCommand(msg % reporter)
        reporter_cls = REPORTERS[reporter]
    else:
        # user defined class
        reporter_cls = reporter

    # verbosity
    if verbosity is None:
        use_verbosity = Task.DEFAULT_VERBOSITY
    else:
        use_verbosity = verbosity
    show_out = use_verbosity < 2 # show on error report

    # outstream
    if isinstance(output, basestring):
        outstream = codecs.open(output, 'w', encoding='utf-8')
    else: # outfile is a file-like object (like StringIO or sys.stdout)
        outstream = output

    # run
    try:
        # FIXME stderr will be shown twice in case of task error/failure
        if isinstance(reporter_cls, type):
            reporter_obj = reporter_cls(outstream, {'show_out':show_out,
                                                    'show_err': True})
        else: # also accepts reporter instances
            reporter_obj = reporter_cls


        if not MRunner.available():
            num_process = 0
            sys.stderr.write("WARNING: multiprocessing module not available, " +
                             "running on single process.")

        if num_process == 0:
            runner = Runner(dependency_file, reporter_obj, continue_,
                            always_execute, verbosity)
        else:
            runner = MRunner(dependency_file, reporter_obj, continue_,
                               always_execute, verbosity, num_process)

        return runner.run_all(task_control)
    finally:
        if isinstance(output, str):
            outstream.close()



