"""Watch for modifications of file-system
use by cmd_auto module
"""

import os.path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

def get_platform_system():
    """return platform.system
    platform module has many regexp, so importing it is slow...
    import only if required
    """
    import platform
    return platform.system()


class FileModifyWatcher(object):
    """Use watchdog to watch file-system for file modifications

    Usage:
    1) subclass the method handle_event, action to be performed
    2) create an object passing a list of files to be watched
    3) call the loop method
    """
    supported_platforms = ('Darwin', 'Linux')

    def __init__(self, path_list):
        """@param file_list (list-str): files to be watched"""
        self.file_list = set()
        self.watch_dirs = set() # all dirs to be watched
        self.notify_dirs = set() # dirs that generate notification whatever file
        for filename in path_list:
            path = os.path.abspath(filename)
            if os.path.isfile(path):
                self.file_list.add(path)
                self.watch_dirs.add(os.path.dirname(path))
            else:
                self.notify_dirs.add(path)
                self.watch_dirs.add(path)
        self.platform = get_platform_system()
        if self.platform not in self.supported_platforms:
            msg = "Unsupported platform '%s'\n" % self.platform
            msg += ("'auto' command is supported only on %s" %
                    (self.supported_platforms,))
            raise Exception(msg)

    def _handle(self, event):
        """Takes care of filtering out all modifications that are
        not in the watch list. Keep the thread going (return True)
        if modification was not one of the watched files, otherwise
        let handle_event take care of it."""
        filename = event.src_path
        if (filename in self.file_list or
            os.path.dirname(filename) in self.notify_dirs):
            return self.handle_event(event)
        return True

    def handle_event(self, event):
        """this should be sub-classed. Return True if you want the
        loop to keep going. Return False if you want it to stop."""
        raise NotImplementedError

    def loop(self):
        """Infinite loop watching for file modifications"""
        handler = self._handle
        is_running = [True]

        class EventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                result = handler(event)
                if not result:
                    is_running[0] = False

        event_handler = EventHandler()
        observer = Observer()

        for watch_this in self.watch_dirs:
            observer.schedule(event_handler, watch_this, recursive=False)
        observer.start()

        try:
            while is_running[0]:
                time.sleep(1)
        except (SystemExit, KeyboardInterrupt):
            pass

        observer.stop()
        observer.join()
