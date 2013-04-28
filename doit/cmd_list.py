from .cmd_base import DoitCmdBase, check_tasks_exist, subtasks_iter

opt_listall = {'name': 'subtasks',
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


    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R'}


    @property
    def dep_manager(self):
        """manager with access to task status (run, up-to-date...)"""
        if not hasattr(self, '_dep_manager'):
            self._dep_manager = self.dep_class(self.dep_file)
        return self._dep_manager


    def _print_task(self, task, col1_len, quiet, status, list_deps):
        """print a single task"""
        col1_fmt = "%%-%ds" % (col1_len + 3)
        task_str = col1_fmt % task.name
        # add doc
        if (not quiet) and task.doc:
            task_str += "%s" % task.doc
        # FIXME group task status is never up-to-date
        if status:
            # FIXME: 'ignore' handling is ugly
            if self.dep_manager.status_is_ignore(task):
                task_status = 'ignore'
            else:
                task_status = self.dep_manager.get_status(task, None)
            task_str = "%s %s" % (self.STATUS_MAP[task_status], task_str)

        self.outstream.write("%s\n" % task_str)

        # print dependencies
        if list_deps:
            for dep in task.file_dep:
                self.outstream.write(" -  %s\n" % dep)
            self.outstream.write("\n")

    @staticmethod
    def _list_filtered(tasks, filter_tasks, include_subtasks):
        """return list of task based on selected 'filter_tasks' """
        check_tasks_exist(tasks, filter_tasks)

        # get task by name
        print_list = []
        for name in filter_tasks:
            task = tasks[name]
            print_list.append(task)
            if include_subtasks:
                print_list.extend(subtasks_iter(tasks, task))
        return print_list


    def _list_all(self, tasks, include_subtasks):
        """list of tasks"""
        print_list = []
        for task in self.task_list:
            if (not include_subtasks) and task.is_subtask:
                continue
            print_list.append(task)
        return print_list


    def _execute(self, subtasks=False, quiet=True, status=False,
                 private=False, list_deps=False, pos_args=None):
        """List task generators, in the order they were defined.
        """
        filter_tasks = pos_args
        # dict of all tasks
        tasks = dict([(t.name, t) for t in self.task_list])

        if filter_tasks:
            # list only tasks passed on command line
            print_list = self._list_filtered(tasks, filter_tasks, subtasks)
        else:
            print_list = self._list_all(tasks, subtasks)

        # exclude private tasks
        if not private:
            print_list = [t for t in print_list if (not t.name.startswith('_'))]

        # print list of tasks
        max_name_len = max(len(t.name) for t in print_list) if print_list else 0
        for task in sorted(print_list):
            self._print_task(task, max_name_len, quiet, status, list_deps)
        return 0
