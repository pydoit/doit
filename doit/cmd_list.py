import sys

from .dependency import Dependency
from .cmd_base import DoitCmdBase

opt_listall = {'name': 'all',
               'short':'',
               'long': 'all',
               'type': bool,
               'default': False,
               'help': "list include all sub-tasks from dodo file"
               }

opt_list_quiet = {'name': 'quiet',
                  'short': 'q',
                  'long': 'quiet',
                  'type': bool,
                  'default': False,
                  'help': 'print just task name (less verbose than default)'}

opt_list_status = {'name': 'status',
                   'short': 's',
                   'long': 'status',
                   'type': bool,
                   'default': False,
                   'help': 'print task status (R)un, (U)p-to-date, (I)gnored'}

opt_list_private = {'name': 'private',
                    'short': 'p',
                    'long': 'private',
                    'type': bool,
                    'default': False,
                    'help': "print private tasks (start with '_')"}

opt_list_dependencies = {'name': 'list_deps',
                         'short': '',
                         'long': 'deps',
                         'type': bool,
                         'default': False,
                         'help': ("print list of dependencies "
                                  "(file dependencies only)")
                         }

class List(DoitCmdBase):
    doc_purpose = "list tasks from dodo file"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_listall, opt_list_quiet, opt_list_status,
                   opt_list_private, opt_list_dependencies)

    def execute(self, params, args):
        """execute cmd 'list' """
        params = self.read_dodo(params, args)
        return self._execute(
            params['dep_file'], self.task_list, sys.stdout,
            args, params['all'], not params['quiet'],
            params['status'], params['private'], params['list_deps'])


    @staticmethod
    def _execute(dependency_file, task_list, outstream, filter_tasks,
                  print_subtasks=False, print_doc=False, print_status=False,
                  print_private=False, print_dependencies=False):
        """List task generators, in the order they were defined.

        @param filter_tasks (list -str): print only tasks from this list
        @param outstream (file-like): object
        @param print_subtasks (bool)
        @param print_doc(bool)
        @param print_status(bool)
        @param print_private(bool)
        @param print_dependencies(bool)
        """
        status_map = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R'}
        def _list_print_task(task, col1_len):
            """print a single task"""
            col1_fmt = "%%-%ds" % (col1_len + 3)
            task_str = col1_fmt % task.name
            # add doc
            if print_doc and task.doc:
                task_str += "%s" % task.doc
            # FIXME this does not take calc_dep into account
            if print_status:
                task_uptodate = dependency_manager.get_status(task, None)
                task_str = "%s %s" % (status_map[task_uptodate], task_str)

            outstream.write("%s\n" % task_str)

            # print dependencies
            if print_dependencies:
                for dep in task.file_dep:
                    outstream.write(" -  %s\n" % dep)
                outstream.write("\n")


        # dict of all tasks
        tasks = dict([(t.name, t) for t in task_list])
        # list only tasks passed on command line
        if filter_tasks:
            base_list = [tasks[name] for name in filter_tasks]
            if print_subtasks:
                for task in base_list:
                    for subt in task.task_dep:
                        if subt.startswith("%s" % task.name):
                            base_list.append(tasks[subt])
        else:
            base_list = task_list
        # status
        if print_status:
            dependency_manager = Dependency(dependency_file)

        print_list = []
        for task in base_list:
            # exclude subtasks (never exclude if filter specified)
            if (not print_subtasks) and (not filter_tasks) and task.is_subtask:
                continue
            # exclude private tasks
            if (not print_private) and task.name.startswith('_'):
                continue
            print_list.append(task)

        max_name_len = max(len(t.name) for t in print_list) if print_list else 0
        for task in sorted(print_list):
            _list_print_task(task, max_name_len)
        return 0
