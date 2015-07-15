"""command doit info - display info on task metadata"""

from __future__ import print_function

import pprint

import six

from .cmd_base import DoitCmdBase
from .exceptions import InvalidCommand



def my_safe_repr(obj, context, maxlevels, level):
    """pretty print supressing unicode prefix

    http://stackoverflow.com/questions/16888409/
           suppress-unicode-prefix-on-strings-when-using-pprint
    """
    typ = type(obj)
    if six.PY2 and typ is six.text_type:
        obj = str(obj)
    return pprint._safe_repr(obj, context, maxlevels, level)


opt_show_build_reason = {
    'name': 'show_build_reason',
    'short': 'R',
    'long': 'show-build-reason',
    'type': bool,
    'default': False,
    'help': """Shows reasons why this target will be rebuild. [default: %(default)s]"""
}


class Info(DoitCmdBase):
    """command doit info"""

    doc_purpose = "show info about a task"
    doc_usage = "TASK"
    doc_description = None

    cmd_options = (opt_show_build_reason, )

    def _execute(self, pos_args, show_build_reason=False):
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

        if show_build_reason:
            if self.dep_manager is None:
                # Avoid failure in tests which don't initialize dep_manager.
                return
            status = self.dep_manager.get_status(task, tasks, get_log=True)
            if status.status == 'up-to-date':
                self.outstream.write('\nIs up to date.\n')
            else:  # status.status == 'run' or status.status == 'error'
                self.outstream.write('\nIs not up to date:\n')
                if status.uptodate_false:
                    self.outstream.write(' * The following uptodate objects evaluate to false:\n')
                    for utd, utd_args, utd_kwargs in status.uptodate_false:
                        self.outstream.write('    - {} (args={}, kwargs={})\n'.format(utd, utd_args, utd_kwargs))
                if status.has_no_dependencies:
                    self.outstream.write(' * The task has no dependencies.\n')
                if status.missing_target:
                    self.outstream.write(' * The following targets do not exist:\n')
                    for target in status.missing_target:
                        self.outstream.write('    - {}\n'.format(target))
                if status.file_dep_checker_changed:
                    self.outstream.write(' * The file_dep checker changed from {0} to {1}.'.format(*status.file_dep_checker_changed))
                if status.added_file_dep:
                    self.outstream.write(' * The following file dependencies were added:\n')
                    for dep in status.added_file_dep:
                        self.outstream.write('    - {}\n'.format(dep))
                if status.removed_file_dep:
                    self.outstream.write(' * The following file dependencies were removed:\n')
                    for dep in status.removed_file_dep:
                        self.outstream.write('    - {}\n'.format(dep))
                if status.missing_file_dep:
                    self.outstream.write(' * The following file dependencies are missing:\n')
                    for dep in status.missing_file_dep:
                        self.outstream.write('    - {}\n'.format(dep))
                if status.changed_file_dep:
                    self.outstream.write(' * The following file dependencies have changed:\n')
                    for dep in status.changed_file_dep:
                        self.outstream.write('    - {}\n'.format(dep))
