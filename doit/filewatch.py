"""Watch for modifications of file-system
use by cmd_auto module
"""

import os.path
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler



class FileModifyWatcher(object):
    """Use watchdog to watch file-system for file modifications

    Usage:
    1) subclass the method handle_event, action to be performed
    2) create an object passing a list of files to be watched
    3) call the loop method
    """

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

    def loop(self, lock_start=None):
        """Infinite loop watching for file modifications"""
        handler = self._handle
        lock = threading.Lock()
        lock.acquire()

        class EventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                result = handler(event)
                if not result:
                    lock.release()

        event_handler = EventHandler()
        observer = Observer()

        for watch_this in self.watch_dirs:
            observer.schedule(event_handler, watch_this, recursive=False)
        observer.start()
        if lock_start:
            lock_start.release()

        try:
            lock.acquire()
        except (SystemExit, KeyboardInterrupt):
            pass

        observer.stop()
        observer.join()
