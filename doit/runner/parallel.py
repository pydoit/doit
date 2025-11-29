"""Parallel task execution runners.

Provides MRunner (multiprocessing) and MThreadRunner (threading) for
parallel task execution. These extend the base Runner with multi-process
or multi-thread execution capabilities.
"""

from multiprocessing import Process, Queue as MQueue
from threading import Thread
import pickle
import queue

try:
    import cloudpickle
    pickle_dumps = cloudpickle.dumps
except ImportError:
    pickle_dumps = pickle.dumps

from ..exceptions import InvalidTask
from ..task import Stream, DelayedLoaded
from .base import Runner
from .executor import TaskExecutor
from .types import ERROR


# Job objects sent from main process to sub-process for execution
class JobHold:
    """Indicates there is no task ready to be executed."""
    type = object()


class JobTask:
    """Contains a Task object (full pickle)."""
    type = object()

    def __init__(self, task):
        self.name = task.name
        try:
            self.task_pickle = pickle_dumps(task)
        # bug on python raising AttributeError
        # https://github.com/python/cpython/issues/73373
        except (pickle.PicklingError, AttributeError) as excp:
            msg = """Error on Task: `{}`.
Task created at execution time that has an attribute than can not be pickled,
so not feasible to be used with multi-processing. To fix this issue make sure
the task is pickable or just do not use multi-processing execution.

Original exception {}: {}
"""
            raise InvalidTask(msg.format(self.name, excp.__class__, excp))


class JobTaskPickle:
    """Dict of Task object excluding attributes that might be unpicklable."""
    type = object()

    def __init__(self, task):
        # actually a dict to be pickled
        self.task_dict = task.pickle_safe_dict()

    @property
    def name(self):
        return self.task_dict['name']


class MReporter:
    """Send reported messages to master process.

    Puts a dictionary {'name': <task-name>, 'reporter': <reporter-method-name>}
    on runner's 'result_q'.
    """

    def __init__(self, runner, reporter_cls):
        self.runner = runner
        self.reporter_cls = reporter_cls

    def __getattr__(self, method_name):
        """Substitute any reporter method with a dispatching method."""
        if not hasattr(self.reporter_cls, method_name):
            raise AttributeError(method_name)

        def rep_method(task):
            self.runner.result_q.put({
                'name': task.name,
                'reporter': method_name,
            })
        return rep_method

    def complete_run(self):
        """Ignore this on MReporter."""
        pass


class MRunner(Runner):
    """MultiProcessing Runner."""
    Queue = staticmethod(MQueue)
    Child = staticmethod(Process)

    @staticmethod
    def available():
        """Check if multiprocessing module is available."""
        # see: https://bitbucket.org/schettino72/doit/issue/17
        #      http://bugs.python.org/issue/3770
        # not available on BSD systems
        try:
            import multiprocessing.synchronize
            multiprocessing  # pyflakes
        except ImportError:  # pragma: no cover
            return False
        else:
            return True

    def __init__(self, dep_manager, reporter,
                 continue_=False, always_execute=False,
                 stream=None, num_process=1):
        Runner.__init__(self, dep_manager, reporter, continue_=continue_,
                        always_execute=always_execute, stream=stream)
        self.num_process = num_process

        self.free_proc = 0   # number of free process
        self.task_dispatcher = None  # TaskDispatcher retrieve tasks
        self.tasks = None    # dict of task instances by name
        self.result_q = None

    def __getstate__(self):
        # multiprocessing on Windows will try to pickle self.
        # These attributes are actually not used by spawned process so
        # safe to be removed.
        pickle_dict = self.__dict__.copy()
        pickle_dict['reporter'] = None
        pickle_dict['task_dispatcher'] = None
        pickle_dict['dep_manager'] = None
        # Executor references dep_manager, so exclude it too
        pickle_dict['_executor'] = None
        return pickle_dict

    def __setstate__(self, state):
        # Restore state
        self.__dict__.update(state)
        # Reconstruct executor (with None dep_manager - will be set up in subprocess)
        self._executor = TaskExecutor(
            dep_manager=None,
            stream=state.get('stream') or Stream(0),
            always_execute=state.get('always_execute', False)
        )

    def get_next_job(self, completed):
        """Get next task to be dispatched to sub-process.

        On MP needs to check if the dependencies finished its execution.

        @returns: - None -> no more tasks to be executed
                  - JobXXX
        """
        if self._stop_running:
            return None  # gentle stop
        node = completed
        while True:
            # get next task from controller
            try:
                node = self.task_dispatcher.generator.send(node)
                if node == "hold on":
                    self.free_proc += 1
                    return JobHold()
            # no more tasks from controller...
            except StopIteration:
                # ... terminate one sub process if no other task waiting
                return None

            # send a task to be executed
            if self.select_task(node, self.tasks):
                # If sub-process already contains the Task object send
                # only safe pickle data, otherwise send whole object.
                task = node.task
                if task.loader is DelayedLoaded and self.Child == Process:
                    return JobTask(task)
                else:
                    return JobTaskPickle(task)

    def _run_tasks_init(self, task_dispatcher):
        """Initialization for run_tasks."""
        self.task_dispatcher = task_dispatcher
        self.tasks = task_dispatcher.tasks

    def _run_start_processes(self, job_q, result_q):
        """Create and start sub-processes.

        @param job_q: (multiprocessing.Queue) tasks to be executed
        @param result_q: (multiprocessing.Queue) collect task results
        @return: list of Process
        """
        proc_list = []
        for _ in range(self.num_process):
            next_job = self.get_next_job(None)
            if next_job is None:
                break  # do not start more processes than tasks
            job_q.put(next_job)
            process = self.Child(
                target=self.execute_task_subprocess,
                args=(job_q, result_q, self.reporter.__class__))
            process.start()
            proc_list.append(process)
        return proc_list

    def _process_result(self, node, task, result):
        """Process result received from sub-process."""
        base_fail = result.get('failure')
        task.update_from_pickle(result['task'])
        for action, output in zip(task.actions, result['out']):
            action.out = output
        for action, output in zip(task.actions, result['err']):
            action.err = output
        self.process_task_result(node, base_fail)

    def run_tasks(self, task_dispatcher):
        """Control subprocesses task dispatching and result collection."""
        # result queue - result collected from sub-processes
        result_q = self.Queue()
        # task queue - tasks ready to be dispatched to sub-processes
        job_q = self.Queue()
        self._run_tasks_init(task_dispatcher)
        proc_list = self._run_start_processes(job_q, result_q)

        # wait for all processes terminate
        proc_count = len(proc_list)
        try:
            while proc_count:
                # wait until there is a result to be consumed
                result = result_q.get()

                if 'exit' in result:
                    raise result['exit'](result['exception'])
                node = task_dispatcher.nodes[result['name']]
                task = node.task
                if 'reporter' in result:
                    getattr(self.reporter, result['reporter'])(task)
                    continue
                self._process_result(node, task, result)

                # update num free process
                free_proc = self.free_proc + 1
                self.free_proc = 0
                # tries to get as many tasks as free process
                completed = node
                for _ in range(free_proc):
                    next_job = self.get_next_job(completed)
                    completed = None
                    if next_job is None:
                        proc_count -= 1
                    job_q.put(next_job)
                # check for cyclic dependencies
                if len(proc_list) <= self.free_proc:
                    raise RuntimeError("Cyclic dependency detected")
        except (SystemExit, KeyboardInterrupt, Exception):
            if self.Child == Process:
                for proc in proc_list:
                    proc.terminate()
            raise
        # we are done, join all process
        for proc in proc_list:
            proc.join()

        # get teardown results
        while not result_q.empty():  # safe because subprocess joined
            result = result_q.get()
            if 'reporter' not in result:
                raise RuntimeError("Unexpected result without reporter")
            task = task_dispatcher.tasks[result['name']]
            getattr(self.reporter, result['reporter'])(task)

    def execute_task_subprocess(self, job_q, result_q, reporter_class):
        """Execute tasks in child process.

        @param job_q: task queue
            * None elements indicate process can terminate
            * JobHold indicate process should wait for next task
            * JobTask / JobTaskPickle task to be executed
        """
        self.result_q = result_q
        if self.Child == Process:
            self.reporter = MReporter(self, reporter_class)
        try:
            while True:
                job = job_q.get()

                if job is None:
                    self.teardown()
                    return  # no more tasks to execute finish this process

                # job is an incomplete Task obj when pickled, attributes
                # that might contain unpicklable data were removed.
                # so we need to get task from this process and update it
                # to get dynamic task attributes.
                if job.type is JobTaskPickle.type:
                    task = self.tasks[job.name]
                    if self.Child == Process:  # pragma: no cover ...
                        # ... actually covered but subprocess doesn't get it.
                        task.update_from_pickle(job.task_dict)

                elif job.type is JobTask.type:
                    task = pickle.loads(job.task_pickle)

                # do nothing. this is used to start the subprocess even
                # if no task is available when process is created.
                else:
                    if job.type is not JobHold.type:
                        raise RuntimeError(f"Unknown job type: {job.type}")
                    continue  # pragma: no cover

                result = {'name': task.name}
                task_failure = self.execute_task(task)
                if task_failure:
                    result['failure'] = task_failure
                result['task'] = task.pickle_safe_dict()
                result['out'] = [action.out for action in task.actions]
                result['err'] = [action.err for action in task.actions]

                result_q.put(result)
        except (SystemExit, KeyboardInterrupt, Exception) as exception:
            # error, blow-up everything. send exception info to master process
            result_q.put({
                'exit': exception.__class__,
                'exception': str(exception)})


class MThreadRunner(MRunner):
    """Parallel runner using threads."""
    Queue = staticmethod(queue.Queue)

    class DaemonThread(Thread):
        """Daemon thread to ensure process terminates if threads aren't joined."""
        def __init__(self, *args, **kwargs):
            Thread.__init__(self, *args, **kwargs)
            self.daemon = True

    Child = staticmethod(DaemonThread)

    @staticmethod
    def available():
        return True
