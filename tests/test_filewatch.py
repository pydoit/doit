import os
import threading

import py.test

from doit.filewatch import FileModifyWatcher


def pytest_funcarg__cwd(request):
    """set cwd to parent folder of this file."""
    def set_cwd():
        cwd = {}
        cwd['previous'] = os.getcwd()
        cwd['current'] = os.path.abspath(os.path.dirname(__file__))
        os.chdir(cwd['current'])
        return cwd
    def restore_cwd(cwd):
        os.chdir(cwd['previous'])
    return request.cached_setup(
        setup=set_cwd,
        teardown=restore_cwd,
        scope="function")


class TestFileWatcher(object):
    def testInit(self, cwd):
        file1, file2 = 'data/w1.txt', 'data/w2.txt'
        fw = FileModifyWatcher((file1, file2))
        # file_list contains absolute paths
        assert os.path.abspath(file1) in fw.file_list
        assert os.path.abspath(file2) in fw.file_list
        # watch_dirs
        assert os.path.join(cwd['current'], 'data') in fw.watch_dirs


    def testUnsuportedPlatform(self, monkeypatch):
        monkeypatch.setattr(FileModifyWatcher, 'supported_platforms', ())
        py.test.raises(Exception, FileModifyWatcher, [])

    def testHandleEventNotSubclassed(self):
        fw = FileModifyWatcher([])
        py.test.raises(NotImplementedError, fw.handle_event, None)

    def testLoop(self, cwd):
        file1, file2, file3 = 'data/w1.txt', 'data/w2.txt', 'data/w3.txt'
        stop_file = 'data/stop'
        fw = FileModifyWatcher((file1, file2, stop_file))
        events = []
        should_stop = []
        started = []
        def handle_event(event):
            events.append(event.pathname)
            if event.pathname.endswith("stop"):
                should_stop.append(True)
        fw.handle_event = handle_event

        def loop_callback(notifier):
            started.append(True)
            # force loop to stop
            if should_stop:
                raise KeyboardInterrupt
        loop_thread = threading.Thread(target=fw.loop, args=(loop_callback,))
        loop_thread.daemon = True
        loop_thread.start()

        # wait watcher to be ready
        while not started: # pragma: no cover
            assert loop_thread.isAlive()

        # write in watched file
        fd = open(file1, 'w')
        fd.write("hi")
        fd.close()
        # write in non-watched file
        fd = open(file3, 'w')
        fd.write("hi")
        fd.close()
        # write in another watched file
        fd = open(file2, 'w')
        fd.write("hi")
        fd.close()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        loop_thread.join(1)
        assert not loop_thread.isAlive()

        assert os.path.abspath(file1) == events[0]
        assert os.path.abspath(file2) == events[1]
