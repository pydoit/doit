"""extra goodies to be used in dodo files"""

import os
import time
import datetime
import hashlib


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
            config_digest = hashlib.md5(data).hexdigest()
        else:
            raise Exception(('Invalid type of config_changed parameter got %s,' +
                             'must be string or dict') % (type(config),))

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
            return {'success-time': time.time()}
        task.insert_action(save_now)
        last_success = values.get('success-time', None)
        if last_success is None:
            return False
        return (time.time() - last_success) < limit_sec
    return uptodate_timeout


# debug helper
def set_trace(): # pragma: no cover
    """start debugger, make sure stdout shows pdb output.
    output is not restored.
    """
    import pdb
    import sys
    sys.stdout = sys.__stdout__
    pdb.Pdb().set_trace(sys._getframe().f_back) #pylint: disable=W0212

