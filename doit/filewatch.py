"""Watch for modifications of file-system
use by cmd_auto module
"""

import os.path
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def get_platform_system():
    """return platform.system
    platform module has many regexp, so importing it is slow...
    import only if required
    """
    import platform
    return platform.system()


class FileModifyWatcher(object):
    """Use inotify to watch file-system for file modifications

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
        self.observer = Observer()
        self.observer.start()
        while not self.observer.is_alive():
            time.sleep(0.1)


    def __del__(self):
        self.observer.stop()
        self.observer.join()
        
    def _handle(self, event):
        """calls platform specific handler"""
        filename = event.src_path

        if (filename in self.file_list or
            os.path.dirname(filename) in self.notify_dirs):
            self.handle_event(event)

    def handle_event(self, event):
        """this should be sub-classed """
        raise NotImplementedError

    def _loop(self):
        handler = self._handle
        observer = self.observer
        
        class EventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                try:
                    handler(event)
                except KeyboardInterrupt:
                    pass

        event_handler = EventHandler()

        for watch_this in self.watch_dirs:
            observer.schedule(event_handler, watch_this, recursive=False)
        
    def loop(self):
        """Infinite loop watching for file modifications

        """

        self._loop()


