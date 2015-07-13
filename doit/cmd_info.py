"""command doit info - display info on task metadata"""

from __future__ import print_function

import pprint

import six

from .cmd_base import DoitCmdBase
from .exceptions import InvalidCommand
from .dependency import DependencyException



def my_safe_repr(obj, context, maxlevels, level):
    """pretty print supressing unicode prefix

    http://stackoverflow.com/questions/16888409/
           suppress-unicode-prefix-on-strings-when-using-pprint
    """
    typ = type(obj)
    if six.PY2 and typ is six.text_type:
        obj = str(obj)
    return pprint._safe_repr(obj, context, maxlevels, level)


class Info(DoitCmdBase):
    """command doit info"""

    doc_purpose = "show info about a task"
    doc_usage = "TASK"
    doc_description = None

    def _execute(self, pos_args):
        if len(pos_args) != 1:
            msg = ('doit info failed, must select *one* task.'
                   '\nCheck `doit help info`.')
            raise InvalidCommand(msg)

        task_name = pos_args[0]
        # dict of all tasks
        tasks = dict([(t.name, t) for t in self.task_list])

        printer = pprint.PrettyPrinter(indent=4, stream=self.outstream)
        printer.format = my_safe_repr

        task = tasks[task_name]
        task_attrs = (
            'name', 'file_dep', 'task_dep', 'setup_tasks', 'calc_dep',
            'targets',
            # these fields usually contains reference to python functions
            # 'actions', 'clean', 'uptodate', 'teardown', 'title'
            'getargs', 'params', 'verbosity', 'watch'
        )
        for attr in task_attrs:
            value = getattr(task, attr)
            # by default only print fields that have non-empty value
            if value:
                self.outstream.write('\n{0}:'.format(attr))
                printer.pprint(getattr(task, attr))

        if self.dep_manager is None:
            # Avoid failure in tests which don't initialize dep_manager.
            return
        rebuild_log = []
        try:
            status = self.dep_manager.get_status(task, tasks, rebuild_log=rebuild_log)
        except DependencyException:
            # A raised DependencyException means that a file dependency is missing.
            # Since rebuild_log contains the necessary information, we treat this
            # the same as a return value of 'run'.
            status = 'run'
        if status == 'up-to-date':
            self.outstream.write('\nIs up to date.\n')
        else:  # status == 'run'
            self.outstream.write('\nIs not up to date:\n')
            for entry in rebuild_log:
                self.outstream.write('  * {0}\n'.format(entry))
