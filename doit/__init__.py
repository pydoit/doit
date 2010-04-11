"""doit - Automation Tool

The MIT License

Copyright (c) 2008-2010 Eduardo Naufel Schettino

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

__version__ = (0,8,'dev')


import sys
import traceback


class CatchedException(object):
    """This used to save info from catched exceptions
    The traceback from the original exception is saved
    """
    def __init__(self, msg, exception=None):
        self.message = msg
        self.traceback = ''

        if exception is not None:
            self.traceback = traceback.format_exception(
                exception.__class__, exception, sys.exc_info()[2])

    def get_msg(self):
        return "%s\n%s" % (self.message, "".join(self.traceback))

    def get_name(self):
        return self.__class__.__name__


# TODO rename this? should be ActionFailed?
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
