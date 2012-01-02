"""extra goodies to be used in dodo files"""

import os
import time as time_module
import datetime
import hashlib
import operator
import subprocess

from .action import CmdAction


# action
def create_folder(dir_path):
    """create a folder in the given path if it doesnt exist yet."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return True


# title
def title_with_actions(task):
    """return task name task actions"""
    if task.actions:
        title = "\n\t".join([unicode(action) for action in task.actions])
    # A task that contains no actions at all
    # is used as group task
    else:
        title = "Group: %s" % ", ".join(task.task_dep)
    return "%s => %s"% (task.name, title)


# uptodate
def run_once(task, values):
    """execute task just once
    used when user manually manages a dependency
    """
    def save_executed():
        return {'run-once': True}
    task.insert_action(save_executed)
    return values.get('run-once', False)


# uptodate
def config_changed(config):
    """check if passed config was modified
    @var config (str) or (dict)
    """
    def uptodate_config(task, values):
        config_digest = None
        if isinstance(config, basestring):
            config_digest = config
        elif isinstance(config, dict):
            data = ''
            for key in sorted(config):
                data += key + str(config[key])
            if isinstance(data, unicode): # pragma: no cover # python3
                byte_data = data.encode("utf-8")
            else:
                byte_data = data
            config_digest = hashlib.md5(byte_data).hexdigest()
        else:
            raise Exception(('Invalid type of config_changed parameter got %s' +
                             ', must be string or dict') % (type(config),))

        def save_config():
            return {'_config_changed': config_digest}
        task.insert_action(save_config)
        last_success = values.get('_config_changed')
        if last_success is None:
            return False
        return (last_success == config_digest)
    return uptodate_config


# uptodate
def timeout(timeout_limit):
    """add timeout to task

    @param timeout_limit: (datetime.timedelta, int) in seconds

    if the time elapsed since last time task was executed is bigger than
    the "timeout" time the task is NOT up-to-date
    """

    if isinstance(timeout_limit, datetime.timedelta):
        limit_sec = (timeout_limit.days * 24 * 3600) + timeout_limit.seconds
    elif isinstance(timeout_limit, int):
        limit_sec = timeout_limit
    else:
        msg = "timeout should be datetime.timedelta or int got %r "
        raise Exception(msg % timeout_limit)

    def uptodate_timeout(task, values):
        def save_now():
            return {'success-time': time_module.time()}
        task.insert_action(save_now)
        last_success = values.get('success-time', None)
        if last_success is None:
            return False
        return (time_module.time() - last_success) < limit_sec
    return uptodate_timeout


# uptodate
class check_timestamp_unchanged(object):
    """check if timestamp of a given file/dir is unchanged since last run.

    The C{cmp_op} parameter can be used to customize when timestamps are
    considered unchanged, e.g. you could pass L{operator.ge} to also consider
    e.g. files reverted to an older copy as unchanged; or pass a custom
    function to completely customize what unchanged means.

    If the specified file does not exist, an exception will be raised.  Note
    that if the file C{fn} is a target of another task you should probably add
    C{task_dep} on that task to ensure the file is created before checking it.
    """
    def __init__(self, file_name, time='mtime', cmp_op=operator.eq):
        """initialize the callable

        @param fn: (str) path to file/directory to check
        @param time: (str) which timestamp field to check, can be one of
                     (atime, access, ctime, status, mtime, modify)
        @param cmp_op: (callable) takes two parameters (prev_time, current_time)
                   should return True if the timestamp is considered unchanged

        @raises ValueError: if invalid C{time} value is passed
        """
        if time in ('atime', 'access'):
            self._timeattr = 'st_atime'
        elif time in ('ctime', 'status'):
            self._timeattr = 'st_ctime'
        elif time in ('mtime', 'modify'):
            self._timeattr = 'st_mtime'
        else:
            raise ValueError('time can be one of: atime, access, ctime, '
                             'status, mtime, modify (got: %r)' % time)
        self._file_name = file_name
        self._cmp_op = cmp_op
        self._key = '.'.join([self._file_name, self._timeattr])

    def _get_time(self):
        return getattr(os.stat(self._file_name), self._timeattr)

    def __call__(self, task, values):
        """register action that saves the timestamp and check current timestamp

        @raises OSError: if cannot stat C{self._file_name} file
                         (e.g. doesn't exist)
        """
        def save_now():
            return {self._key: self._get_time()}
        task.insert_action(save_now)

        prev_time = values.get(self._key)
        if prev_time is None: # this is first run
            return False
        current_time = self._get_time()
        return self._cmp_op(prev_time, current_time)


# action
class InteractiveAction(CmdAction):
    """Action to handle Interactive shell process:
        * the output is never captured
        * it is always successful (return code is not used)
        * "swallow" KeyboardInterrupt
    """
    def execute(self, out=None, err=None):
        action = self.expand_action()
        process = subprocess.Popen(action, shell=True)
        try:
            process.wait()
        except KeyboardInterrupt:
            pass # normal way to stop interactive process


# debug helper
def set_trace(): # pragma: no cover
    """start debugger, make sure stdout shows pdb output.
    output is not restored.
    """
    import pdb
    import sys
    debugger = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back) #pylint: disable=W0212

