import sys
import os
import re

from .action import CmdAction
from .task import Task
from .cmd_run import Run


class Strace(Run):
    doc_purpose = "use strace to list file_deps and targets"
    doc_usage = "TASK"
    doc_description = """
The output is a list of files prefixed with 'D' for dependency
or 'T' for target. The full strace output can be found at '.strace'.
The files are listed in chronological order and might appear more than once.

This is a debugging feature wiht many lilmitations.
  * can strace only one task at a time
  * can only strace CmdAction
  * if there is more than one action .strace file is overwritten
  * the process being traced itself might have some kind of cache,
    that means it might not write a target file if it exist.

So this is NOT 100% reliable, use with care!
Error message might not be very clear...
"""

    cmd_options = ()

    TRACE_CMD = "strace -f -e trace=file -o %s %s "
    TRACE_OUT = '.strace'

    def execute(self, params, args):
        if os.path.exists(self.TRACE_OUT):
            os.unlink(self.TRACE_OUT)
        assert len(args) == 1, 'doit strace failed, must select task to strace'
        return Run.execute(self, params, args)

    def _execute(self):
        # find task to trace and wrap it
        selected = self.sel_tasks[0]
        for task in self.task_list:
            if task.name == selected:
                self.wrap_strace(task)
                break

        # add task to print report
        report_strace = Task(
            'strace_report',
            actions = [(find_deps, [self.TRACE_OUT])],
            verbosity = 2,
            task_dep = [selected],
            uptodate = [False],
        )
        self.task_list.append(report_strace)
        self.sel_tasks.append(report_strace.name)

        # clear strace file
        return Run._execute(self, sys.stdout)


    @classmethod
    def wrap_strace(cls, task):
        wrapped_actions = []
        for action in task.actions:
            cmd = cls.TRACE_CMD % (cls.TRACE_OUT, action._action)
            wrapped = CmdAction(cmd, task, save_out=action.save_out)
            wrapped_actions.append(wrapped)
        task._action_instances = wrapped_actions


def find_deps(strace_out):
    """read file witn strace output, return dict with deps, targets"""
    # 7978  open("/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
    # ignore text until '('
    # get "file" name inside "
    # comma-space separate other elements ', '
    # ignore elments if inside []
    # get "mode" file was open, until ')' is closed
    # ignore rest of line
    regex = re.compile(r'.*\("(?P<file>[^"]*)", (\[.*\])*(?P<mode>[^)]*)\).*')

    with open(strace_out) as text:
        for line in text:
            match = regex.match(line)
            if not match:
                continue
            name = os.path.abspath(match.group('file'))
            if 'WR' in match.group('mode'):
                print "T ", name
            else:
                print "D ", name


