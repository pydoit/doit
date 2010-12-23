"""Reports doit execution status/results"""

import sys
import time
import datetime
import StringIO

from doit.dependency import json


class ConsoleReporter(object):
    """Default reporter. print results on console/terminal (stdout/stderr)

    @ivar show_out (bool): include captured stdout on failure report
    @ivar show_err (bool): include captured stderr on failure report
    """
    def __init__(self, outstream, options):
        # save non-succesful result information (include task errors)
        self.failures = []
        self.aborted = None
        self.show_out = options.get('show_out', True)
        self.show_err = options.get('show_err', True)
        self.outstream = outstream

    def get_status(self, task):
        """called when task is selected (check if up-to-date)"""
        pass

    def execute_task(self, task):
        """called when excution starts"""
        # ignore tasks that do not define actions
        if task.actions:
            self.outstream.write('.  %s\n' % task.title())

    def add_failure(self, task, exception):
        """called when excution finishes with a failure"""
        self.failures.append({'task': task, 'exception':exception})

    def add_success(self, task):
        """called when excution finishes successfuly"""
        pass

    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        self.outstream.write("-- %s\n" % task.title())

    def skip_ignore(self, task):
        """skipped ignored task"""
        self.outstream.write("!! %s\n" % task.title())


    def cleanup_error(self, exception):
        """error during cleanup"""
        sys.stderr.write(exception.get_msg())

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        pass

    def runtime_error(self, msg):
        """called when an error occurs"""
        self.aborted = msg

    def complete_run(self):
        """called when finshed running all tasks"""
        # if test fails print output from failed task
        for result in self.failures:
            self.outstream.write("#"*40 + "\n")
            msg = '%s - taskid:%s\n' % (result['exception'].get_name(),
                                        result['task'].name)
            self.outstream.write(msg)
            self.outstream.write(result['exception'].get_msg())
            self.outstream.write("\n")
            task = result['task']
            if self.show_out:
                out = "".join([a.out for a in task.actions if a.out])
                self.outstream.write("%s\n" % out)
            if self.show_err:
                err = "".join([a.err for a in task.actions if a.err])
                self.outstream.write("%s\n" % err)

        if self.aborted is not None:
            self.outstream.write("#"*40 + "\n")
            self.outstream.write("Execution aborted.\n")
            self.outstream.write(self.aborted)

class ExecutedOnlyReporter(ConsoleReporter):
    """No output for skipped (up-to-date) and group tasks

    Produces zero output unless a task is executed
    """
    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        pass

    def skip_ignore(self, task):
        """skipped ignored task"""
        pass



class TaskResult(object):
    """result object used by JsonReporter"""
    # FIXME what about returned value from python-actions ?
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
        """called when task starts its execution"""
        self._started_on = time.time()

    def set_result(self, result):
        """called when task finishes its execution"""
        self._finished_on = time.time()
        self.result = result
        line_sep = "\n<------------------------------------------------>\n"
        self.out = line_sep.join([a.out for a in self.task.actions if a.out])
        self.err = line_sep.join([a.err for a in self.task.actions if a.err])

    def to_dict(self):
        """convert result data to dictionary"""
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
    """output results in JSON format

    - out (str)
    - err (str)
    - tasks (list - dict):
         - name (str)
         - result (str)
         - out (str)
         - err (str)
         - started (str)
         - elapsed (float)
    """
    def __init__(self, outstream, options=None):
        # options parameter is not used
        assert options is None
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
        self.aborted = None

    def get_status(self, task):
        """called when task is selected (check if up-to-date)"""
        self.t_results[task.name] = TaskResult(task)

    def execute_task(self, task):
        """called when excution starts"""
        self.t_results[task.name].start()

    def add_failure(self, task, exception):
        """called when excution finishes with a failure"""
        self.t_results[task.name].set_result('fail')
        # TODO save exception

    def add_success(self, task):
        """called when excution finishes successfuly"""
        self.t_results[task.name].set_result('success')

    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        self.t_results[task.name].set_result('up-to-date')

    def skip_ignore(self, task):
        """skipped ignored task"""
        self.t_results[task.name].set_result('ignore')

    def cleanup_error(self, exception):
        """error during cleanup"""
        # TODO same as runtime_error
        pass

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        pass

    def runtime_error(self, msg):
        """called when an error occurs"""
        self.aborted = msg

    def complete_run(self):
        """called when finshed running all tasks"""
        # restore stdout
        log_out = sys.stdout.getvalue()
        sys.stdout = self._old_out
        log_err = sys.stderr.getvalue()
        sys.stderr = self._old_err

        if self.aborted is not None:
            log_err += self.aborted

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
