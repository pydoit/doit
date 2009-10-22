import sys
import time
import datetime

from doit.dependency import json


class FakeReporter(object):
    """Just log everything in internal attribute - used on tests"""
    def __init__(self):
        self.log = []

    def start_task(self, task):
        pass

    def execute_task(self, task):
        # FIXME
        self.log.append(('start', task))

    def add_failure(self, task, exception):
        self.log.append(('fail', task))

    def add_success(self, task):
        self.log.append(('success', task))

    def skip_uptodate(self, task):
        self.log.append(('skip', task))

    def cleanup_error(self, exception):
        self.log.append(('cleanup_error',))

    def complete_run(self):
        pass


class ConsoleReporter(object):
    """Default reporter. print results on console/terminal (stdout/stderr)

    @ivar show_out (bool): include captured stdout on failure report
    @ivar show_err (bool): include captured stderr on failure report
    """
    def __init__(self, show_out, show_err):
        # save non-succesful result information (include task errors)
        self.failures = []
        self.show_out = show_out
        self.show_err = show_err


    def start_task(self, task):
        pass

    def execute_task(self, task):
        print task.title()

    def add_failure(self, task, exception):
        self.failures.append({'task': task, 'exception':exception})

    def add_success(self,task):
        pass

    def skip_uptodate(self, task):
        print "---", task.title()


    def cleanup_error(self, exception):
        sys.stderr.write(exception.get_msg())


    def complete_run(self):
        # if test fails print output from failed task
        for result in self.failures:
            sys.stderr.write("#"*40 + "\n")
            sys.stderr.write('%s: %s\n' % (result['exception'].get_name(),
                                           result['task'].name))
            sys.stderr.write(result['exception'].get_msg())
            sys.stderr.write("\n")
            task = result['task']
            if self.show_out:
                out = "".join([a.out for a in task.actions if a.out])
                sys.stderr.write("%s\n" % out)
            if self.show_err:
                err = "".join([a.err for a in task.actions if a.err])
                sys.stderr.write("%s\n" % err)




class TaskResult(object):
    def __init__(self, name):
        self.name = name
        self.result = None
        self.log = None
        self.started = None
        self.elapsed = None
        self._started_on = None
        self._finished_on = None

    def execute(self):
        self._started_on = time.time()

    def set_result(self, task, result):
        self._finished_on = time.time()
        self.result = result
        # FIXME DRY
        out = "".join([a.out for a in task.actions if a.out])
        err = "".join([a.err for a in task.actions if a.err])
        self.log = ("--err--\n" + err + "--out--\n" + out)

    def to_dict(self):
        if self._started_on is not None:
            self.started =str(datetime.datetime.utcfromtimestamp(self._started_on))
            self.elapsed = self._finished_on - self._started_on
        return {'name': self.name,
                'result': self.result,
                'log': self.log,
                'started': self.started,
                'elapsed': self.elapsed}


class JsonReporter(object):
    """save results in a file using JSON"""
    def __init__(self, filename):
        self._filename = filename
        self.t_results = {}

    def start_task(self, task):
        self.t_results[task.name] = TaskResult(task.name)

    def execute_task(self, task):
        self.t_results[task.name].execute()

    def add_failure(self, task, exception):
        self.t_results[task.name].set_result(task, 'fail')

    def add_success(self, task):
        self.t_results[task.name].set_result(task, 'success')

    def skip_uptodate(self, task):
        self.t_results[task.name].set_result(task, 'up-to-date')

    def cleanup_error(self, exception):
        # TODO ???
        pass

    def complete_run(self):
        json_data = [tr.to_dict() for tr in self.t_results.itervalues()]
        try:
            fp = open(self._filename,'w')
            json.dump(json_data, fp)
        finally:
            fp.close()

