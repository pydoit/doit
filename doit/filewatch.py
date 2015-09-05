"""Watch for modifications of file-system
use by cmd_auto module
"""

import os.path
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, EVENT_TYPE_MOVED



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


    def _filter(self, event):
        """Check if event should really trigger the handler

        :return bool: should trigger handler
        """
        # get path based on event type
        if event.event_type == EVENT_TYPE_MOVED:
            filename = event.dest_path
        else:
            filename = event.src_path
        # check path is being watched
        if filename in self.file_list:
            return True
        if os.path.dirname(filename) in self.notify_dirs:
            return True
        return False


    def handle_event(self, event):
        """this should be sub-classed. Return True if you want the
        loop to keep going. Return False if you want it to stop."""
        raise NotImplementedError

    def loop(self, lock_start=None):
        """Infinite loop watching for file modifications"""
        handler = self.handle_event
        event_filter = self._filter
        lock = threading.Lock()
        lock.acquire()

        class EventHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                if event_filter(event):
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
