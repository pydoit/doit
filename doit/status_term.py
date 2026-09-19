"""terminal I/O of the interactive `doit status`: raw key input and screen
control with ANSI escape sequences. Standard library only.

POSIX uses termios/select. Windows uses msvcrt, and the console must accept
ANSI escape sequences (Windows 10 and later).
"""

import os
import shutil
import sys
import time


class TuiUnavailable(Exception):
    """the interactive screen can not be used here"""


# keys are named 'left', 'right', 'up', 'down', 'enter', 'esc', or the
# character typed
_ESCAPES = {'[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left',
            'OA': 'up', 'OB': 'down', 'OC': 'right', 'OD': 'left'}
_WINDOWS_KEYS = {'H': 'up', 'P': 'down', 'M': 'right', 'K': 'left'}


def parse_key(data):
    """name of the first key in bytes read from a POSIX terminal"""
    if data.startswith('\x1b'):
        return _ESCAPES.get(data[1:3], 'esc' if len(data) == 1 else 'other')
    if data[:1] in ('\r', '\n'):
        return 'enter'
    if data[:1] == '\x03':
        return 'esc'  # Ctrl-C ends the screen like esc
    return data[:1]


ENTER_SCREEN = '\x1b[?1049h\x1b[?25l'  # alternate screen, hide cursor
LEAVE_SCREEN = '\x1b[?25h\x1b[?1049l'
CLEAR = '\x1b[H\x1b[2J'


class Terminal:
    """what `status_tui.run` needs from a terminal"""

    def __init__(self, out=None):
        self.out = out or sys.stdout

    def __enter__(self):
        self.setup()
        self.out.write(ENTER_SCREEN)
        self.out.flush()
        return self

    def __exit__(self, *exc):
        self.out.write(LEAVE_SCREEN)
        self.out.flush()
        self.restore()

    def size(self):
        """@return: (columns, rows)"""
        return tuple(shutil.get_terminal_size((80, 24)))

    def write(self, text):
        self.out.write(text)
        self.out.flush()

    def setup(self):
        raise NotImplementedError()  # pragma: no cover

    def restore(self):
        raise NotImplementedError()  # pragma: no cover

    def read_key(self, timeout):
        """@return: key name, None if no key came within `timeout` seconds"""
        raise NotImplementedError()  # pragma: no cover


class PosixTerminal(Terminal):

    def __init__(self, out=None):
        super().__init__(out)
        try:
            import termios
            import tty
            import select
        except ImportError:
            raise TuiUnavailable('no termios on this platform')
        self._termios, self._tty, self._select = termios, tty, select
        self.fd = sys.stdin.fileno()

    def setup(self):
        self._saved = self._termios.tcgetattr(self.fd)
        # cbreak keeps Ctrl-C working
        self._tty.setcbreak(self.fd)

    def restore(self):
        self._termios.tcsetattr(self.fd, self._termios.TCSADRAIN, self._saved)

    def read_key(self, timeout):
        if not self._select.select([self.fd], [], [], timeout)[0]:
            return None
        return parse_key(os.read(self.fd, 32).decode('utf-8', 'ignore'))


class WindowsTerminal(Terminal):

    def __init__(self, out=None):
        super().__init__(out)
        import msvcrt
        self._msvcrt = msvcrt

    def setup(self):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)) or \
                not kernel32.SetConsoleMode(handle, mode.value | 0x4):
            raise TuiUnavailable(
                'this console does not support ANSI escape sequences')
        self._handle, self._mode = handle, mode.value

    def restore(self):
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(self._handle, self._mode)

    def read_key(self, timeout):
        msvcrt = self._msvcrt
        end = time.monotonic() + timeout
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ('\x00', '\xe0'):  # arrow keys come in two parts
                    return _WINDOWS_KEYS.get(msvcrt.getwch(), 'other')
                return parse_key(char)
            if time.monotonic() >= end:
                return None
            time.sleep(0.02)


def open_terminal(out=None):
    """terminal of the current platform. Raises TuiUnavailable if stdin or
    stdout is not a terminal."""
    out = out or sys.stdout
    if not (sys.stdin.isatty() and out.isatty()):
        raise TuiUnavailable('needs a terminal for input and output')
    return WindowsTerminal(out) if os.name == 'nt' else PosixTerminal(out)
