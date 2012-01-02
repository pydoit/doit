"""Task runner"""

import sys
from multiprocessing import Process, Queue

from .exceptions import InvalidTask, CatchedException
from .exceptions import TaskFailed, SetupError, DependencyError
from .dependency import Dependency
from .task import Task


# execution result.
SUCCESS = 0
FAILURE = 1
ERROR = 2


class Runner(object):
    """Task runner

    run_all()
      run_tasks():
        for each task:
            select_task()
            execute_task()
            process_task_result()
      finish()

    """
    def __init__(self, dependency_file, reporter, continue_=False,
                 always_execute=False, verbosity=0):
        """@param dependency_file: (string) file path of the db file
        @param reporter: reporter to be used. It can be a class or an object
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param verbosity: (int) 0,1,2 see Task.execute
        """
        self.dependency_manager = Dependency(dependency_file)
        self.reporter = reporter
        self.continue_ = continue_
        self.always_execute = always_execute
        self.verbosity = verbosity

        self.teardown_list = [] # list of tasks to be teardown
        self.final_result = SUCCESS # until something fails
        self._stop_running = False


    def _handle_task_error(self, task, catched_excp):
        """handle all task failures/errors

        called whenever there is an error before executing a task or
        its execution is not successful.
        """
        assert isinstance(catched_excp, CatchedException)
        self.dependency_manager.remove_success(task)
        self.reporter.add_failure(task, catched_excp)
        # only return FAILURE if no errors happened.
        if isinstance(catched_excp, TaskFailed):
            self.final_result = FAILURE
        else:
            self.final_result = ERROR
        if not self.continue_:
            self._stop_running = True


    def select_task(self, task):
        """Returns bool, task should be executed
         * side-effect: set task.options

        Tasks should be executed if they are not up-to-date.

        Tasks that cointains setup-tasks must be selected twice,
        so it gives chance for dependency tasks to be executed after
        checking it is not up-to-date.
        """

        # if run_status is not None, it was already calculated
        if task.run_status is None:
            self.reporter.get_status(task)

            # check if task is up-to-date
            try:
                task.run_status = self.dependency_manager.get_status(task)
            except Exception, exception:
                msg = "ERROR: Task '%s' checking dependencies" % task.name
                dep_error = DependencyError(msg, exception)
                self._handle_task_error(task, dep_error)
                return False

            if not self.always_execute:
                # if task is up-to-date skip it
                if task.run_status == 'up-to-date':
                    self.reporter.skip_uptodate(task)
                    task.values = self.dependency_manager.get_values(task.name)
                    return False
                # check if task should be ignored (user controlled)
                if task.run_status == 'ignore':
                    self.reporter.skip_ignore(task)
                    return False

            if task.setup_tasks:
                # dont execute now, execute setup first...
                return False
        else:
            # sanity checks
            assert task.run_status == 'run', \
                "%s:%s" % (task.name, task.run_status)
            assert task.setup_tasks

        # selected just need to get values from other tasks
        for arg, value in task.getargs.iteritems():
            try:
                task.options[arg] = self.dependency_manager.get_value(value)
            except Exception, exception:
                msg = ("ERROR getting value for argument '%s'\n" % arg +
                       str(exception))
                self._handle_task_error(task, DependencyError(msg))
                return False

        return True


    def execute_task(self, task):
        """execute task's actions"""
        # register cleanup/teardown
        if task.teardown:
            self.teardown_list.append(task)

        # finally execute it!
        self.reporter.execute_task(task)
        return task.execute(sys.stdout, sys.stderr, self.verbosity)


    def process_task_result(self, task, catched_excp):
        """handles result"""
        task.run_status = "done"
        # save execution successful
        if catched_excp is None:
            self.dependency_manager.save_success(task)
            self.reporter.add_success(task)
        # task error
        else:
            self._handle_task_error(task, catched_excp)


    def run_tasks(self, task_control):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param task_control: L{TaskControl}
        """
        for task in task_control.task_dispatcher():
            if self._stop_running:
                break
            if not self.select_task(task):
                continue
            catched_excp = self.execute_task(task)
            self.process_task_result(task, catched_excp)


    def teardown(self):
        """run teardown from all tasks"""
        for task in reversed(self.teardown_list):
            self.reporter.teardown_task(task)
            catched = task.execute_teardown(sys.stdout, sys.stderr,
                                            self.verbosity)
            if catched:
                msg = "ERROR: task '%s' teardown action" % task.name
                error = SetupError(msg, catched)
                self.reporter.cleanup_error(error)


    def finish(self):
        """finish running tasks"""
        # flush update dependencies
        self.dependency_manager.close()
        self.teardown()

        # report final results
        self.reporter.complete_run()
        return self.final_result


    def run_all(self, task_control):
        """entry point to run tasks"""
        try:
            self.run_tasks(task_control)
        except InvalidTask, exception:
            self.reporter.runtime_error(str(exception))
        finally:
            self.finish()
        return self.final_result


class Hold(object):
    """Sentinel class: No task ready to be executed"""
    pass

class MRunner(Runner):
    """MultiProcessing Runner """

    class MReporter(object):
        """send reported messages to master process

        puts a dictionary {'name': <task-name>,
                           'reporter': <reporter-method-name>}
        on runner's 'result_q'
        """
        def __init__(self, runner, original_reporter):
            self.runner = runner
            self.original_reporter = original_reporter

        def __getattr__(self, method_name):
            """substitute any reporter method with a dispatching method"""
            if not hasattr(self.original_reporter, method_name):
                raise AttributeError(method_name)
            def rep_method(task):
                self.runner.result_q.put({'name':task.name,
                                          'reporter':method_name})
            return rep_method

        def complete_run(self):
            """ignore this on MReporter"""
            pass

    def __init__(self, dependency_file, reporter, continue_=False,
                 always_execute=False, verbosity=0, num_process=1):
        Runner.__init__(self, dependency_file, reporter, continue_,
                        always_execute, verbosity)
        self.num_process = num_process

        # key: name of task that has not completed yet
        # value: list of task names that are waiting for task in key
        self.waiting = {}

        # list of task names that are ready to be executed (these were waiting)
        self.ready_queue = []
        self.free_proc = 0   # number of free process
        self.task_gen = None # genrator to retrieve tasks from controller
        self.tasks = None    # dict of task instances by name
        self.result_q = None

    def get_next_task(self):
        """get next task to be dispatched to sub-process

        On MP needs to check if the dependencies finished its execution
        @returns: - a task
                  - None -> no more tasks to be executed
                  - Hold object, all tasks are waiting for dependencies
        """
        if self._stop_running:
            return None # gentle stop
        while True:
            # get new task from ready queue
            if self.ready_queue:
                task_name = self.ready_queue.pop(0)
                task = self.tasks[task_name]
            # get next task from controller
            else:
                try:
                    task = self.task_gen.next()
                    if not isinstance(task, Task):
                        self.free_proc += 1
                        return Hold()
                # no more tasks from controller...
                except StopIteration:
                    # ... terminate one sub process if no other task waiting
                    if not self.waiting:
                        return None
                    else:
                        # extra-process might be used by waiting task, hold on
                        self.free_proc += 1
                        return Hold()


            # task with setup must be selected twice...
            wait_for = task.task_dep + list(task.calc_dep)
            # must wait for setup_tasks too if on second select.
            if not (task.setup_tasks and task.run_status is None):
                wait_for += task.setup_tasks

            # check task-dependencies are done
            for dep in  wait_for:
                if (self.tasks[dep].run_status is None or
                    self.tasks[dep].run_status == 'run'):
                    # not ready yet, add to waiting dict and re-start loop
                    # to get another task
                    if dep in self.waiting:
                        self.waiting[dep].append(task.name)
                    else:
                        self.waiting[dep] = [task.name]
                    break
            # dont need to wait for another task
            else:
                if self.select_task(task):
                    return task


    def process_task_result(self, task, catched_excp):
        """handle task result"""
        Runner.process_task_result(self, task, catched_excp)
        if task.name in self.waiting:
            for ready_task in self.waiting[task.name]:
                self.ready_queue.append(ready_task)
            del self.waiting[task.name]


    def _run_tasks_init(self, task_control):
        """initialization for run_tasks"""
        self.task_gen = task_control.task_dispatcher()
        self.tasks = task_control.tasks


    def _run_start_processes(self, task_q, result_q):
        """create and start sub-processes
        @param task_q: (multiprocessing.Queue) tasks to be executed
        @param result_q: (multiprocessing.Queue) collect task results
        @return list of Process
        """
        proc_list = []
        for _ in xrange(self.num_process):
            next_task = self.get_next_task()
            if next_task is None:
                break # do not start more processes than tasks
            if isinstance(next_task, Task):
                task_q.put(next_task)
            else: # next_task is Hold
                # no task ready to be executed but some are on the queue
                # awaiting to be executed
                task_q.put(next_task)
            process = Process(target=self.execute_task_subprocess,
                              args=(task_q, result_q))
            process.start()
            proc_list.append(process)
        return proc_list


    def run_tasks(self, task_control):
        """controls subprocesses task dispatching and result collection
        """
        # result queue - result collected from sub-processes
        result_q = Queue()
        # task queue - tasks ready to be dispatched to sub-processes
        task_q = Queue()
        self._run_tasks_init(task_control)
        proc_list = self._run_start_processes(task_q, result_q)

        # wait for all processes terminate
        proc_count = len(proc_list)
        while proc_count:
            # wait until there is a result to be consumed
            result = result_q.get()
            task = task_control.tasks[result['name']]
            if 'reporter' in result:
                getattr(self.reporter, result['reporter'])(task)
                continue
            elif 'failure' in result:
                catched_excp = result['failure']
            elif 'exit' in result:
                raise result['exit'](result['exception'])
            else:
                catched_excp = None
                task.result = result['result']
                task.values = result['values']

            # completed one task, dispatch next one
            self.process_task_result(task, catched_excp)

            # update num free process
            free_proc = self.free_proc + 1
            self.free_proc = 0
            # tries to get as many tasks as free process
            for _ in range(free_proc):
                next_task = self.get_next_task()
                if next_task is None:
                    proc_count -= 1
                if isinstance(next_task, Task):
                    task_q.put(next_task)
                else:
                    task_q.put(next_task)
            # check for cyclic dependencies
            assert len(proc_list) > self.free_proc

        # we are done, join all process
        for proc in proc_list:
            proc.join()

        # get teardown results
        while not result_q.empty(): # safe because subprocess joined
            result = result_q.get()
            assert 'reporter' in result
            task = task_control.tasks[result['name']]
            getattr(self.reporter, result['reporter'])(task)


    def execute_task_subprocess(self, task_q, result_q):
        """executed on child processes
        @param task_q: task queue,
            * None elements indicate process can terminate
            * Hold indicate process should wait for next task
            * Task task to be executed
        """
        self.result_q = result_q
        self.reporter = self.MReporter(self, self.reporter)
        try:
            while True:
                recv_task = task_q.get()
                if recv_task is None:
                    self.teardown()
                    return # no more tasks to execute finish this process

                # do nothing. this used to start the subprocess even if no task
                # is available when process is created.
                if isinstance(recv_task, Hold):
                    continue

                # recv_task is an incomplete obj. when pickled, attrbiutes
                # that might contain unpickleble data were removed.
                # so we need to get task from this process and update it
                # to get dynamic task attributes.
                task = self.tasks[recv_task.name]
                task.update_from_pickle(recv_task)

                result = {'name': task.name}
                t_result = self.execute_task(task)

                if t_result is None:
                    result['result'] = task.result
                    result['values'] = task.values
                else:
                    result['failure'] = t_result
                result_q.put(result)
        except (SystemExit, KeyboardInterrupt, Exception), exception:
            # error, blow-up everything. send exception info to master process
            result_q.put({'name': task.name,
                          'exit': exception.__class__,
                          'exception': str(exception)})

