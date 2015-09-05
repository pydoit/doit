import os
import sys
import threading
import signal
import multiprocessing
import shutil

import six
import pytest
from watchdog.events import FileSystemMovedEvent

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


    def testHandleEventNotSubclassed(self):
        fw = FileModifyWatcher([])
        pytest.raises(NotImplementedError, fw.handle_event, None)


    def test_filter_file_move(self, restore_cwd, tmpdir):
        files = ('data/w1.txt', 'data/w2.txt')
        tmpdir.mkdir('data')
        for fname in files:
            tmpdir.join(fname).open('a').close()
        os.chdir(tmpdir.strpath)

        fw = FileModifyWatcher((files[0],))
        # fake events
        # move watched file doesnt doesnt trigger anything
        event = FileSystemMovedEvent(os.path.abspath(files[0]),
                                     os.path.abspath(files[1]))
        assert not fw._filter(event)
        # move TO watched file triggers
        event2 = FileSystemMovedEvent(os.path.abspath(files[1]),
                                     os.path.abspath(files[0]))
        assert fw._filter(event2)


    @pytest.mark.skipif(str(sys.platform.startswith("darwin")))
    def testLoop(self, restore_cwd, tmpdir):
        files = ['data/w1.txt', 'data/w2.txt', 'data/w3.txt']
        stop_file = 'data/stop'

        # create data files
        tmpdir.mkdir('data')
        for fname in files + [stop_file]:
            tmpdir.join(fname).open('a').close()
        os.chdir(tmpdir.strpath)

        fw = FileModifyWatcher((files[0], files[1], stop_file))
        lock_start = threading.Lock()
        lock_start.acquire()
        events = []
        def handle_event(event):
            events.append(event.src_path)
            if event.src_path.endswith("stop"):
                return False
            return True
        fw.handle_event = handle_event

        loop_thread = threading.Thread(target=fw.loop, args=[lock_start])
        loop_thread.daemon = True
        loop_thread.start()

        # Make sure loop has time to start
        lock_start.acquire()

        # write in watched file
        fd = open(files[0], 'w')
        fd.write("hi")
        fd.close()
        assert loop_thread.isAlive()

        # write in non-watched file
        fd = open(files[2], 'w')
        fd.write("hi")
        fd.close()
        assert loop_thread.isAlive()

        # write in another watched file
        fd = open(files[1], 'w')
        fd.write("hi")
        fd.close()
        assert loop_thread.isAlive()

        # tricky to stop watching
        fd = open(stop_file, 'w')
        fd.write("hi")
        fd.close()
        loop_thread.join()

        print(files)
        print(events)
        assert os.path.abspath(files[0]) == events[0]
        assert os.path.abspath(files[1]) == events[1]


    # this test hangs on python2. I dont know why.
    @pytest.mark.skipif(str(six.PY2 and sys.platform.startswith("linux")))
    @pytest.mark.skipif(str(sys.platform.startswith("darwin")))
    def testExit(self, restore_cwd, tmpdir):
        # create data files
        stop_file = 'data/stop'
        tmpdir.mkdir('data')
        tmpdir.join(stop_file).open('a').close()
        os.chdir(tmpdir.strpath)

        lock_start = multiprocessing.Lock()
        lock_start.acquire()

        fw = FileModifyWatcher([stop_file])
        proc = multiprocessing.Process(target=fw.loop, args=[lock_start])
        proc.start()

        lock_start.acquire()  # wait for loop
        os.kill(proc.pid, signal.SIGINT)
        proc.join()
