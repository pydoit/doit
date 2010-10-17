"""cmd-line functions"""
import sys
import os.path
import itertools
import platform

from doit import dependency
from doit.task import Task
from doit.control import TaskControl, InvalidCommand
from doit.runner import Runner, MP_Runner
from doit.reporter import REPORTERS
from doit.dependency import Dependency


def doit_run(dependency_file, task_list, output, options=None,
             verbosity=None, always_execute=False, continue_=False,
             reporter='default', num_process=0):
    """
    @param reporter: (str) one of provided reporters or ...
                     (class) user defined reporter class (can only be specified
           from DOIT_CONFIG - never from command line)
    """
    # get tasks to be executed
    task_control = TaskControl(task_list)
    task_control.process(options)

    # reporter
    if isinstance(reporter, str):
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
    if isinstance(output, str):
        outstream = open(output, 'w')
    else: # outfile is a file-like object (like StringIO or sys.stdout)
        outstream = output

    # run
    try:
        # FIXME stderr will be shown twice in case of task error/failure
        reporter_obj = reporter_cls(outstream, show_out , True)

        if num_process == 0:
            runner = Runner(dependency_file, reporter_obj, continue_,
                            always_execute, verbosity)
        else:
            runner = MP_Runner(dependency_file, reporter_obj, continue_,
                               always_execute, verbosity, num_process)

        runner.run_tasks(task_control)
        return runner.finish()
    finally:
        if isinstance(output, str):
            outstream.close()



def doit_clean(task_list, outstream, dryrun, clean_dep, clean_tasks):
    """Clean tasks
    @param task_list (list - L{Task}): list of all tasks from dodo file
    @ivar dryrun (bool): if True clean tasks are not executed
                        (just print out what would be executed)
    @param clean_tasks (list - string): tasks bo be clean. clean all if
                                        empty list.
    @param clean_dep (bool): execute clean from task_dep

    """
    tasks = dict([(t.name, t) for t in task_list])
    cleaned = set()

    def clean_task(task_name):
        """wrapper to ensure task clean-action is executed only once"""
        if task_name not in cleaned:
            cleaned.add(task_name)
            tasks[task_name].clean(outstream, dryrun)

    # clean all tasks if none specified
    if not clean_tasks:
        clean_tasks = [t.name for t in task_list]

    for name in clean_tasks:
        if clean_dep:
            for task_dep in tasks[name].task_dep:
                clean_task(task_dep)
        clean_task(name)




def doit_list(dependency_file, task_list, outstream, filter_tasks,
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
    def _list_print_task(task):
        """print a single task"""
        task_str = task.name
        # add doc
        if print_doc and task.doc:
            task_str += "\t* %s" % task.doc
        if print_status:
            task_uptodate = dependency_manager.get_status(task)
            task_str = "%s %s" % (status_map[task_uptodate], task_str)

        outstream.write("%s\n" % task_str)

        # print dependencies
        if print_dependencies:
            for dep in task.file_dep:
                outstream.write(" -  %s\n" % dep)
            outstream.write("\n")

        # print subtasks
        if print_subtasks:
            for subt in task.task_dep:
                if subt.startswith("%s" % task.name):
                    _list_print_task(tasks[subt])

    # dict of all tasks
    tasks = dict([(t.name, t) for t in task_list])
    # list only tasks passed on command line
    if filter_tasks:
        print_tasks = [tasks[name] for name in filter_tasks]
    else:
        print_tasks = task_list
    # status
    if print_status:
        dependency_manager = Dependency(dependency_file)

    for task in print_tasks:
        # exclude subtasks (never exclude if filter specified)
        if (not filter_tasks) and task.is_subtask:
            continue
        # exclude private tasks
        if (not print_private) and task.name.startswith('_'):
            continue
        _list_print_task(task)
    return 0


def doit_forget(dependency_file, task_list, outstream, forget_tasks):
    """remove saved data successful runs from DB
    @param dependency_file: (str)
    @param task_list: (Task) tasks from dodo file
    @param forget_tasks: (list - str) tasks to be removed. remove all if
                         empty list.
    """
    dependency_manager = dependency.Dependency(dependency_file)
    # no task specified. forget all
    if not forget_tasks:
        dependency_manager.remove_all()
        outstream.write("forgeting all tasks\n")
    # forget tasks from list
    else:
        tasks = dict([(t.name, t) for t in task_list])
        for task_name in forget_tasks:
            # check task exist
            if task_name not in tasks:
                msg = "'%s' is not a task."
                raise InvalidCommand(msg % task_name)
            # for group tasks also remove all tasks from group.
            group = [task_name]
            while group:
                to_forget = group.pop(0)
                if not tasks[to_forget].actions:
                    # get task dependencies only from group-task
                    group.extend(tasks[to_forget].task_dep)
                # forget it - remove from dependency file
                dependency_manager.remove(to_forget)
                outstream.write("forgeting %s\n" % to_forget)
    dependency_manager.close()


def doit_ignore(dependency_file, task_list, outstream, ignore_tasks):
    """mark tasks to be ignored
    @param dependency_file: (str)
    @param task_list: (Task) tasks from dodo file
    @param ignore_tasks: (list - str) tasks to be ignored.
    """
    # no task specified.
    if not ignore_tasks:
        outstream.write("You cant ignore all tasks! Please select a task.\n")
        return

    dependency_manager = dependency.Dependency(dependency_file)
    tasks = dict([(t.name, t) for t in task_list])
    for task_name in ignore_tasks:
        # check task exist
        if task_name not in tasks:
            msg = "'%s' is not a task."
            raise InvalidCommand(msg % task_name)
        # for group tasks also remove all tasks from group.
        # FIXME: DRY
        group = [task_name]
        while group:
            to_ignore = group.pop(0)
            if not tasks[to_ignore].actions:
                # get task dependencies only from group-task
                group.extend(tasks[to_ignore].task_dep)
            # ignore it - remove from dependency file
            dependency_manager.ignore(tasks[to_ignore])
            outstream.write("ignoring %s\n" % to_ignore)
    dependency_manager.close()



class FileModifyWatcher(object):
    """Use inotify to watch file-system for file modifications

    Usage:
    1) subclass the method handle_event, action to be performed
    2) create an object passing a list of files to be watched
    3) call the loop method
    """
    supported_platforms = ('Darwin', 'Linux')

    def __init__(self, file_list):
        """@param file_list (list-str): files to be watched"""
        self.file_list = set([os.path.abspath(f) for f in file_list])
        self.watch_dirs = set([os.path.dirname(f) for f in self.file_list])
        self.notifier = None
        self.platform = platform.system()
        if self.platform not in self.supported_platforms:
            msg = "Unsupported platform '%s'\n" % self.platform
            msg += ("'auto' command is supported only on %s" %
                    (self.supported_platforms,))
            raise Exception(msg)

    def _handle(self, event):
        if self.platform == 'Darwin':
            if event.name in self.file_list:
                self.handle_event(event)
        elif self.platform == 'Linux':
            if event.pathname in self.file_list:
                self.handle_event(event)

    def handle_event(self, event):
        """this should be sub-classed """
        raise NotImplementedError


    def _loop_darwin(self):
        """loop implementation for darwin platform"""
        from fsevents import Observer
        from fsevents import Stream
        from fsevents import IN_MODIFY

        observer = Observer()
        handler = self._handle
        def fsevent_callback(event):
            if event.mask == IN_MODIFY:
                handler(event)

        for watch_this in self.watch_dirs:
            stream = Stream(fsevent_callback, watch_this, file_events=True)
            observer.schedule(stream)

        observer.daemon = True
        observer.start()
        try:
            # hack to keep main thread running...
            import time
            while True:
                time.sleep(99999)
        except (SystemExit, KeyboardInterrupt):
            pass


    def _loop_linux(self, loop_callback):
        """loop implementation for linux platform"""
        import pyinotify
        handler = self._handle
        class EventHandler(pyinotify.ProcessEvent):
            def process_default(self, event):
                handler(event)

        watch_manager = pyinotify.WatchManager()
        mask = pyinotify.IN_CLOSE_WRITE
        event_handler = EventHandler()
        self.notifier = pyinotify.Notifier(watch_manager, event_handler)

        for watch_this in self.watch_dirs:
            watch_manager.add_watch(watch_this, mask)

        self.notifier.loop(loop_callback)


    def loop(self, loop_callback=None):
        """Infinite loop watching for file modifications
        @loop_callback: used to stop loop on unittests
        """

        if self.platform == 'Darwin':
            self._loop_darwin()

        elif self.platform == 'Linux':
            self._loop_linux(loop_callback)

def doit_auto(dependency_file, task_list, filter_tasks, loop_callback=None):
    """Re-execute tasks automatically a depedency changes

    @param filter_tasks (list -str): print only tasks from this list
    @loop_callback: used to stop loop on unittests
    """
    task_control = TaskControl(task_list)
    task_control.process(filter_tasks)
    tasks_to_run = list(set([t for t in task_control.task_dispatcher(True)]))
    watch_tasks = [t.name for t in tasks_to_run]
    watch_files = list(itertools.chain(*[s.file_dep for s in tasks_to_run]))
    watch_files = list(set(watch_files))

    class DoitAutoRun(FileModifyWatcher):
        """Execute doit on event handler of file changes """
        def handle_event(self, event):
            doit_run(dependency_file, task_list, sys.stdout,
                     watch_tasks, reporter='executed-only')
            # reset run_status
            for task in task_list:
                task.run_status = None

    file_watcher = DoitAutoRun(watch_files)
    # always run once when started
    file_watcher.handle_event(None)
    file_watcher.loop(loop_callback)

