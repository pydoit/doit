"""Watch for modifications of file-system
use by cmd_auto module
"""

import os.path

from .compat import get_platform_system


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

    def _handle(self, event):
        """calls platform specific handler"""
        if self.platform == 'Darwin': # pragma: no cover
            filename = event.name
        elif self.platform == 'Linux':
            filename = event.pathname
        if (filename in self.file_list or
            os.path.dirname(filename) in self.notify_dirs):
            self.handle_event(event)

    def handle_event(self, event):
        """this should be sub-classed """
        raise NotImplementedError


    def _loop_darwin(self): # pragma: no cover
        """loop implementation for darwin platform"""
        from fsevents import Observer #pylint: disable=F0401
        from fsevents import Stream #pylint: disable=F0401
        from fsevents import IN_MODIFY #pylint: disable=F0401

        observer = Observer()
        handler = self._handle
        def fsevent_callback(event):
            if event.mask == IN_MODIFY:
                handler(event)

        for watch_this in self.watch_dirs:
            stream = Stream(fsevent_callback, watch_this, file_events=True)
            observer.schedule(stream)

        observer.daemon = True
        observer.run()


    def _loop_linux(self, loop_callback):
        """loop implementation for linux platform"""
        import pyinotify
        handler = self._handle
        class EventHandler(pyinotify.ProcessEvent):
            def process_default(self, event):
                handler(event)

        watch_manager = pyinotify.WatchManager()
        event_handler = EventHandler()
        notifier = pyinotify.Notifier(watch_manager, event_handler)

        mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO
        for watch_this in self.watch_dirs:
            watch_manager.add_watch(watch_this, mask)

        notifier.loop(loop_callback)


    def loop(self, loop_callback=None):
        """Infinite loop watching for file modifications
        @loop_callback: used to stop loop on unittests
        """

        if self.platform == 'Darwin': # pragma: no cover
            self._loop_darwin()

        elif self.platform == 'Linux':
            self._loop_linux(loop_callback)
