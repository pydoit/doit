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


opt_show_execute_status = {
    'name': 'show_execute_status',
    'short': 's',
    'long': 'status',
    'type': bool,
    'default': False,
    'help': """Shows reasons why this task would be executed.
 [default: %(default)s]"""
}


class Info(DoitCmdBase):
    """command doit info"""

    doc_purpose = "show info about a task"
    doc_usage = "TASK"
    doc_description = None

    cmd_options = (opt_show_execute_status, )

    def _execute(self, pos_args, show_execute_status=False):
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

        # print reason task is not up-to-date
        if show_execute_status:
            status = self.dep_manager.get_status(task, tasks, get_log=True)
            if status.status == 'up-to-date':
                self.outstream.write('\nTask is up-to-date.\n')
                return 0
            else:  # status.status == 'run' or status.status == 'error'
                self.outstream.write('\nTask is not up-to-date:\n')
                self.outstream.write(self.get_reasons(status.reasons))
                self.outstream.write('\n')
                return 1


    @staticmethod
    def get_reasons(reasons):
        '''return string with description of reason task is not up-to-date'''
        lines = []
        if reasons['has_no_dependencies']:
            lines.append(' * The task has no dependencies.')

        if reasons['uptodate_false']:
            lines.append(' * The following uptodate objects evaluate to false:')
            for utd, utd_args, utd_kwargs in reasons['uptodate_false']:
                msg = '    - {} (args={}, kwargs={})'
                lines.append(msg.format(utd, utd_args, utd_kwargs))

        if reasons['checker_changed']:
            msg = ' * The file_dep checker changed from {0} to {1}.'
            lines.append(msg.format(*reasons['checker_changed']))

        sentences = {
            'missing_target': 'The following targets do not exist:',
            'changed_file_dep': 'The following file dependencies have changed:',
            'missing_file_dep': 'The following file dependencies are missing:',
            'removed_file_dep': 'The following file dependencies were removed:',
            'added_file_dep': 'The following file dependencies were added:',
        }
        for reason, sentence in sentences.items():
            entries = reasons.get(reason)
            if entries:
                lines.append(' * {}'.format(sentence))
                for item in entries:
                    lines.append('    - {}'.format(item))
        return '\n'.join(lines)
