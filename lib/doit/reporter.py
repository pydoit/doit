import sys
import time
import datetime
import StringIO

from doit.dependency import json


class FakeReporter(object):
    """Just log everything in internal attribute - used on tests"""
    def __init__(self):
        self.log = []

    def start_task(self, task):
        self.log.append(('start', task))

    def execute_task(self, task):
        self.log.append(('execute', task))

    def add_failure(self, task, exception):
        self.log.append(('fail', task))

    def add_success(self, task):
        self.log.append(('success', task))

    def skip_uptodate(self, task):
        self.log.append(('up-to-date', task))

    def skip_ignore(self, task):
        self.log.append(('ignore', task))

    def cleanup_error(self, exception):
        self.log.append(('cleanup_error',))

    def complete_run(self):
        pass


class ConsoleReporter(object):
    """Default reporter. print results on console/terminal (stdout/stderr)

    @ivar show_out (bool): include captured stdout on failure report
    @ivar show_err (bool): include captured stderr on failure report
    """
    def __init__(self, outstream, show_out, show_err):
        # save non-succesful result information (include task errors)
        self.failures = []
        self.show_out = show_out
        self.show_err = show_err
        self.outstream = outstream

    def start_task(self, task):
        pass

    def execute_task(self, task):
        # ignore tasks that do not define actions
        if task.actions:
            self.outstream.write('.  %s\n' % task.title())

    def add_failure(self, task, exception):
        self.failures.append({'task': task, 'exception':exception})

    def add_success(self,task):
        pass

    def skip_uptodate(self, task):
        self.outstream.write("---%s\n" % task.title())

    def skip_ignore(self, task):
        self.outstream.write("!!!%s\n" % task.title())


    def cleanup_error(self, exception):
        sys.stderr.write(exception.get_msg())


    def complete_run(self):
        # if test fails print output from failed task
        for result in self.failures:
            self.outstream.write("#"*40 + "\n")
            self.outstream.write('%s: %s\n' % (result['exception'].get_name(),
                                               result['task'].name))
            self.outstream.write(result['exception'].get_msg())
            self.outstream.write("\n")
            task = result['task']
            if self.show_out:
                out = "".join([a.out for a in task.actions if a.out])
                self.outstream.write("%s\n" % out)
            if self.show_err:
                err = "".join([a.err for a in task.actions if a.err])
                self.outstream.write("%s\n" % err)



class ExecutedOnlyReporter(ConsoleReporter):
    """No output for skipped (up-to-date) and group tasks

    Produces zero output unless a task is executed
    """
    def skip_uptodate(self,task):
        pass

    def skip_ignore(self,task):
        pass



class TaskResult(object):
    # FIXME what about returned value from python-actions ?
    # FIXME save raised exceptions
    def __init__(self, task):
        self.task = task
        self.result = None # fail, success, up-to-date, ignore
        self.out = None # stdout from task
        self.err = None # stderr from task
        self.started = None # datetime when task execution started
        self.elapsed = None # time (in secs) taken to execute task
        self._started_on = None # timestamp
        self._finished_on = None # timestamp

    def start(self):
        self._started_on = time.time()

    def set_result(self, result):
        self._finished_on = time.time()
        self.result = result
        # FIXME DRY
        line_sep = "\n<------------------------------------------------>\n"
        self.out = line_sep.join([a.out for a in self.task.actions if a.out])
        self.err = line_sep.join([a.err for a in self.task.actions if a.err])

    def to_dict(self):
        if self._started_on is not None:
            started = datetime.datetime.utcfromtimestamp(self._started_on)
            self.started = str(started)
            self.elapsed = self._finished_on - self._started_on
        return {'name': self.task.name,
                'result': self.result,
                'out': self.out,
                'err': self.err,
                'started': self.started,
                'elapsed': self.elapsed}


class JsonReporter(object):
    """save results in a file using JSON"""
    def __init__(self, outstream, show_out=None, show_err=None):
        # show_out, show_err parameters are ignored.
        # json result is sent to stdout when doit finishes running
        self.t_results = {}
        # when using json reporter output can not contain any other output
        # than the json data. so anything that is sent to stdout/err needs to
        # be captured.
        self._old_out = sys.stdout
        sys.stdout = StringIO.StringIO()
        self._old_err = sys.stderr
        sys.stderr = StringIO.StringIO()
        self.outstream = outstream

    def start_task(self, task):
        self.t_results[task.name] = TaskResult(task)

    def execute_task(self, task):
        self.t_results[task.name].start()

    def add_failure(self, task, exception):
        self.t_results[task.name].set_result('fail')

    def add_success(self, task):
        self.t_results[task.name].set_result('success')

    def skip_uptodate(self, task):
        self.t_results[task.name].set_result('up-to-date')

    def skip_ignore(self, task):
        self.t_results[task.name].set_result('ignore')

    def cleanup_error(self, exception):
        # TODO ???
        pass

    def complete_run(self):
        # restore stdout
        log_out = sys.stdout.getvalue()
        sys.stdout = self._old_out
        log_err = sys.stderr.getvalue()
        sys.stderr = self._old_err

        task_result_list = [tr.to_dict() for tr in self.t_results.itervalues()]
        json_data = {'tasks': task_result_list,
                     'out': log_out,
                     'err': log_err}
        # indent not available on simplejson 1.3 (debian etch)
        # json.dump(json_data, sys.stdout, indent=4)
        json.dump(json_data, self.outstream)


# name of reporters class available to be selected on cmd line
REPORTERS = {'default': ConsoleReporter,
             'executed-only': ExecutedOnlyReporter,
             'json': JsonReporter,
             }
