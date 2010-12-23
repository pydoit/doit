"""Watch for modifications of file-system"""

import os.path
import platform


class FileModifyWatcher(object):
    """Use inotify to watch file-system for file modifications

    Usage:
    1) subclass the method handle_event, action to be performed
    2) create an object passing a list of files to be watched
    3) call the loop method
    """
    supported_platforms = ('Darwin', 'Linux')

    def __init__(self, file_list):
        """@param file_list (list-str): files to be watched"""
        self.file_list = set([os.path.abspath(f) for f in file_list])
        self.watch_dirs = set([os.path.dirname(f) for f in self.file_list])
        self.notifier = None
        self.platform = platform.system()
        if self.platform not in self.supported_platforms:
            msg = "Unsupported platform '%s'\n" % self.platform
            msg += ("'auto' command is supported only on %s" %
                    (self.supported_platforms,))
            raise Exception(msg)

    def _handle(self, event):
        """calls platform specific handler"""
        if self.platform == 'Darwin': # pragma: no cover
            if event.name in self.file_list:
                self.handle_event(event)
        elif self.platform == 'Linux':
            if event.pathname in self.file_list:
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
        observer.start()
        try:
            # hack to keep main thread running...
            import time
            while True:
                time.sleep(99999)
        except (SystemExit, KeyboardInterrupt):
            pass


    def _loop_linux(self, loop_callback):
        """loop implementation for linux platform"""
        import pyinotify
        handler = self._handle
        class EventHandler(pyinotify.ProcessEvent):
            def process_default(self, event):
                handler(event)

        watch_manager = pyinotify.WatchManager()
        mask = pyinotify.IN_CLOSE_WRITE #pylint: disable=E1101
        event_handler = EventHandler()
        self.notifier = pyinotify.Notifier(watch_manager, event_handler)

        for watch_this in self.watch_dirs:
            watch_manager.add_watch(watch_this, mask)

        self.notifier.loop(loop_callback)


    def loop(self, loop_callback=None):
        """Infinite loop watching for file modifications
        @loop_callback: used to stop loop on unittests
        """

        if self.platform == 'Darwin': # pragma: no cover
            self._loop_darwin()

        elif self.platform == 'Linux':
            self._loop_linux(loop_callback)

