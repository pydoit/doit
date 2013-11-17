import os
import threading

import pytest

from doit.filewatch import FileModifyWatcher



class TestFileWatcher(object):
    def testInit(self, restore_cwd, tmpdir):
        dir1 = 'data3'
        files = ('data/w1.txt', 'data/w2.txt')
        tmpdir.mkdir('data')
        for fname in files:
            tmpdir.join(fname).open('a').close()
        os.chdir(tmpdir.strpath)

        fw = FileModifyWatcher((files[0], files[1], dir1))
        # file_list contains absolute paths
        assert 2 == len(fw.file_list)
        assert os.path.abspath(files[0]) in fw.file_list
        assert os.path.abspath(files[1]) in fw.file_list
        # watch_dirs
        assert 2 == len(fw.watch_dirs)
        assert tmpdir.join('data') in fw.watch_dirs
        assert tmpdir.join('data3') in fw.watch_dirs
        # notify_dirs
        assert 1 == len(fw.notify_dirs)
        assert tmpdir.join('data3') in fw.notify_dirs


    def testUnsuportedPlatform(self, monkeypatch):
        monkeypatch.setattr(FileModifyWatcher, 'supported_platforms', ())
        pytest.raises(Exception, FileModifyWatcher, [])

    def testHandleEventNotSubclassed(self):
        fw = FileModifyWatcher([])
        pytest.raises(NotImplementedError, fw.handle_event, None)

    def testLoop(self, restore_cwd, tmpdir):
        files = ['data/w1.txt', 'data/w2.txt', 'data/w3.txt']
        stop_file = 'data/stop'
        tmpdir.mkdir('data')
        for fname in files + [stop_file]:
            tmpdir.join(fname).open('a').close()
        os.chdir(tmpdir.strpath)

        fw = FileModifyWatcher((files[0], files[1], stop_file))
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
        fd = open(files[0], 'w')
        fd.write("hi")
        fd.close()
        # write in non-watched file
        fd = open(files[2], 'w')
        fd.write("hi")
        fd.close()
        # write in another watched file
        fd = open(files[1], 'w')
        fd.write("hi")
        fd.close()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        loop_thread.join(1)
        assert not loop_thread.isAlive()

        assert os.path.abspath(files[0]) == events[0]
        assert os.path.abspath(files[1]) == events[1]
