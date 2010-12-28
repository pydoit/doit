"""Handle exceptions generated from 'user' code"""

import sys
import traceback


class InvalidCommand(Exception):
    """Invalid command line argument."""
    pass

class InvalidDodoFile(Exception):
    """Invalid dodo file"""
    pass

class InvalidTask(Exception):
    """Invalid task instance. User error on specifying the task."""
    pass


class CatchedException(object):
    """This used to save info from catched exceptions
    The traceback from the original exception is saved
    """
    def __init__(self, msg, exception=None):
        self.message = msg
        self.traceback = ''

        if isinstance(exception, CatchedException):
            self.traceback = exception.traceback
        elif exception is not None:
            # TODO remove doit-code part from traceback
            self.traceback = traceback.format_exception(
                exception.__class__, exception, sys.exc_info()[2])


    def get_msg(self):
        """return full exception description (includes traceback)"""
        return "%s\n%s" % (self.message, "".join(self.traceback))

    def get_name(self):
        """get Exception name"""
        return self.__class__.__name__

    def __repr__(self):
        return "(<%s> %s)" % (self.get_name(), self.message)

    def __str__(self):
        return "%s\n%s" % (self.get_name(), self.get_msg())



class TaskFailed(CatchedException):
    """Task execution was not successful."""
    pass


class TaskError(CatchedException):
    """Error while trying to execute task."""
    pass


class SetupError(CatchedException):
    """Error while trying to execute setup object"""
    pass


class DependencyError(CatchedException):
    """Error while trying to check if task is up-to-date"""
    pass


