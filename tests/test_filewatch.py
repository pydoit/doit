import os
import time
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
        def handle_event(event):
            events.append(event.src_path)
            if event.src_path.endswith("stop"):
                should_stop.append(True)
                return False
            return True
        fw.handle_event = handle_event

        loop_thread = threading.Thread(target=fw.loop)
        loop_thread.daemon = True
        loop_thread.start()

        # Make sure loop has time to start
        time.sleep(1)

        # write in watched file
        fd = open(files[0], 'w')
        fd.write("hi")
        fd.close()
        time.sleep(1)
        assert loop_thread.isAlive()

        # write in non-watched file
        fd = open(files[2], 'w')
        fd.write("hi")
        fd.close()
        time.sleep(1)
        assert loop_thread.isAlive()

        # write in another watched file
        fd = open(files[1], 'w')
        fd.write("hi")
        fd.close()
        time.sleep(1)
        assert loop_thread.isAlive()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        time.sleep(1)
        loop_thread.join(1)

        if loop_thread.isAlive(): # pragma: no cover
            # this test is very flaky so we give it one more chance...
            # write on file to terminate thread
            fd = open(stop_file, 'w')
            fd.write("hi")
            fd.close()

            loop_thread.join(1)
            if loop_thread.is_alive(): # pragma: no cover
                raise Exception("thread not terminated")

        assert os.path.abspath(files[0]) == events[0]
        assert os.path.abspath(files[1]) == events[1]

    def testExit(self, restore_cwd, tmpdir):
        files = ['data/w1.txt', 'data/w2.txt', 'data/w3.txt']
        tmpdir.mkdir('data')
        for fname in files:
            tmpdir.join(fname).open('a').close()
        os.chdir(tmpdir.strpath)

        fw = FileModifyWatcher((files[0], files[1]))
        events = []
        should_stop = []
        def handle_event(event):
            events.append(event.src_path)
            if event.src_path.endswith("stop"):
                should_stop.append(True)
                return False
            return True
        fw.handle_event = handle_event

        def stopper():
            time.sleep(.1)
            try:
                # Python 2
                import thread
                thread.interrupt_main()
            except ImportError:
                # Python 3
                import _thread
                _thread.interrupt_main()

        # Create a thread that will stop the main thread
        loop_thread = threading.Thread(target=stopper)
        loop_thread.daemon = True
        loop_thread.start()

        # This will block until a SystemExit or
        # KeyboardInterrupt is raised
        fw.loop()
