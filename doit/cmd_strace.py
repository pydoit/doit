import sys
import os
import re

from .action import CmdAction
from .task import Task
from .cmd_run import Run


# filter to display only files from cwd
opt_show_all = {
    'name':'show_all',
    'short':'a',
    'long':'all',
    'type': bool,
    'default': False,
    'help': "display all files (not only from within CWD path",
    }


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
  * does not handle chdir

So this is NOT 100% reliable, use with care!
Error message might not be very clear...
"""

    cmd_options = (opt_show_all, )

    TRACE_CMD = "strace -f -e trace=file -o %s %s "
    TRACE_OUT = '.strace'

    def execute(self, params, args):
        """remove existing output file if any and do sanity checking"""
        if os.path.exists(self.TRACE_OUT):
            os.unlink(self.TRACE_OUT)
        assert len(args) == 1, 'doit strace failed, must select task to strace'
        return Run.execute(self, params, args)

    def _execute(self, show_all):
        # find task to trace and wrap it
        selected = self.sel_tasks[0]
        for task in self.task_list:
            if task.name == selected:
                self.wrap_strace(task)
                break

        # add task to print report
        report_strace = Task(
            'strace_report',
            actions = [(find_deps, [self.outstream, self.TRACE_OUT, show_all])],
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
        """wrap task actions into strace command"""
        wrapped_actions = []
        for action in task.actions:
            cmd = cls.TRACE_CMD % (cls.TRACE_OUT, action._action)
            wrapped = CmdAction(cmd, task, save_out=action.save_out)
            wrapped_actions.append(wrapped)
        task._action_instances = wrapped_actions
        task._extend_uptodate([False])


def find_deps(outstream, strace_out, show_all):
    """read file witn strace output, return dict with deps, targets"""
    # 7978  open("/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
    # get "mode" file was open, until ')' is closed
    # ignore rest of line
    # .*\(                 # ignore text until '('
    # "(?P<file>[^"]*)"    # get "file" name inside "
    # , (\[.*\])*          # ignore elments if inside [] - used by execve
    # (?P<mode>[^)]*)\)    # get mode opening file
    #  = ].*               # check syscall was successful""",
    regex = re.compile(r'.*\("(?P<file>[^"]*)", (\[.*\])*(?P<mode>[^)]*)\) = [^-].*')

    read = set()
    write = set()
    cwd = os.getcwd()
    with open(strace_out) as text:
        for line in text:
            # ignore non file operation
            match = regex.match(line)
            if not match:
                continue
            rel_name = match.group('file')
            name = os.path.abspath(rel_name)

            # ignore files out of cwd
            if not show_all:
                if not name.startswith(cwd):
                    continue

            if 'WR' in match.group('mode'):
                if name not in write:
                    write.add(name)
                    outstream.write("W %s\n" % name)
            else:
                if name not in read:
                    read.add(name)
                    outstream.write("R %s\n" % name)

