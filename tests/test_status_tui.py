import unittest

from doit.cmd_status import Style
from doit.status_term import TuiUnavailable, open_terminal, parse_key
import io
import re

from doit.status_tui import (
    HINTS, ASCII_HINTS, Navigator, build_frame, draw, frame_lines, run,
    task_window, window_start)

# a -> b -> d, a -> c -> d, e alone
PARENTS = {'a': [], 'b': ['a'], 'c': ['a'], 'd': ['b', 'c'], 'e': []}
CHILDREN = {'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': [], 'e': []}
STATES = {'a': 'run', 'b': 'may-rerun', 'c': 'may-rerun', 'd': 'may-rerun',
          'e': 'up-to-date'}


def nav(focus):
    return Navigator(PARENTS, CHILDREN, STATES, {'a': [' * changed']}, focus)


class TestNavigatorNoFocus(unittest.TestCase):

    def test_focus_column_lists_all_tasks(self):
        n = nav(None)
        self.assertEqual(n.column_items('focus'), ['a', 'b', 'c', 'd', 'e'])
        self.assertEqual(n.column_items('parents'), [])
        self.assertEqual(n.column_items('children'), [])
        self.assertEqual(n.selected(), 'a')

    def test_up_down_then_enter_focuses_task(self):
        n = nav(None)
        n.down()
        n.down()
        n.enter()
        self.assertEqual(n.focus, 'c')
        self.assertEqual(n.column_items('parents'), ['a'])
        self.assertEqual(n.column_items('children'), ['d'])

    def test_left_right_stay_in_list(self):
        n = nav(None)
        n.right()
        n.left()
        self.assertEqual(n.column, 'focus')

    def test_cursor_starts_on_first_task(self):
        n = nav(None)
        self.assertEqual((n.column, n.cursor, n.selected()),
                         ('focus', 0, 'a'))

    def test_frame_shows_all_tasks(self):
        style = Style(color=False, ascii_only=True)
        spans, _, _ = build_frame(nav(None), style, 90, 12, cursor=True)
        texts = [s.text for s in spans if s.x == 30]
        for name in 'abcde':
            self.assertTrue(any(t.endswith(name) for t in texts), name)
        self.assertIn('tasks', texts)


class TestTaskWindow(unittest.TestCase):

    def test_fits(self):
        self.assertEqual(task_window(5, 2, 20), (0, 5, 0, 0))

    def test_centered_and_cut_off(self):
        self.assertEqual(task_window(30, 15, 20), (11, 9, 11, 10))
        self.assertEqual(task_window(30, 0, 20), (0, 9, 0, 21))
        self.assertEqual(task_window(30, 29, 20), (21, 9, 21, 0))

    def test_markers_take_rows(self):
        start, size, above, below = task_window(30, 15, 6)
        self.assertLessEqual(size + bool(above) + bool(below), 6)
        self.assertLessEqual(start, 15 < start + size and 15)

    def test_window_start(self):
        self.assertEqual(window_start(30, 15, 9), 11)


class TestNavigator(unittest.TestCase):

    def test_focus_column_lists_all_tasks_cursor_on_focus(self):
        n = nav('c')
        self.assertEqual(n.column_items('focus'), ['a', 'b', 'c', 'd', 'e'])
        self.assertEqual((n.column, n.cursor, n.selected()),
                         ('focus', 2, 'c'))

    def test_moving_back_to_focus_column_returns_to_focus(self):
        n = nav('c')
        n.down()
        n.right()
        n.left()
        self.assertEqual(n.selected(), 'c')

    def test_focus_selected_by_default(self):
        n = nav('b')
        self.assertEqual(n.column_items('parents'), ['a'])
        self.assertEqual(n.column_items('children'), ['d'])
        self.assertEqual(n.column, 'focus')
        self.assertEqual(n.selected(), 'b')

    def test_left_right_step_through_three_columns(self):
        n = nav('b')
        n.right()
        self.assertEqual((n.column, n.selected()), ('children', 'd'))
        n.right()  # no column further right
        self.assertEqual(n.column, 'children')
        n.left()
        self.assertEqual(n.column, 'focus')
        n.left()
        self.assertEqual((n.column, n.selected()), ('parents', 'a'))

    def test_empty_column_is_skipped(self):
        n = nav('a')  # no parents
        n.left()
        self.assertEqual(n.column, 'focus')
        n = nav('d')  # no children
        n.right()
        self.assertEqual(n.column, 'focus')

    def test_up_down_clamped(self):
        n = nav('a')
        n.right()
        n.up()
        self.assertEqual(n.cursor, 0)
        n.down()
        n.down()
        n.down()
        self.assertEqual(n.cursor, 1)
        self.assertEqual(n.selected(), 'c')

    def test_up_down_in_focus_column(self):
        n = nav('a')
        n.down()
        self.assertEqual(n.selected(), 'b')
        n.up()
        n.up()
        self.assertEqual(n.selected(), 'a')
        n = nav('e')
        n.down()
        self.assertEqual(n.selected(), 'e')

    def test_enter_in_focus_column_refocuses(self):
        n = nav('a')
        n.down()
        n.enter()
        self.assertEqual((n.focus, n.selected()), ('b', 'b'))
        self.assertEqual(n.column_items('parents'), ['a'])

    def test_column_change_resets_cursor(self):
        n = nav('d')
        n.left()
        n.down()
        self.assertEqual(n.selected(), 'c')
        n.right()
        n.left()
        self.assertEqual(n.selected(), 'b')

    def test_enter_refocuses_and_selects_new_focus(self):
        n = nav('d')
        n.left()
        n.down()
        n.enter()
        self.assertEqual(n.focus, 'c')
        self.assertEqual((n.column, n.cursor, n.selected()), ('focus', 2, 'c'))

    def test_enter_on_focus_is_noop(self):
        n = nav('e')
        n.enter()
        self.assertEqual((n.focus, n.column), ('e', 'focus'))

    def test_update_keeps_focus_and_selection(self):
        n = nav('b')
        n.right()
        n.update(dict(STATES, d='up-to-date'), {})
        self.assertEqual(n.selected(), 'd')
        self.assertEqual(n.states['d'], 'up-to-date')
        self.assertEqual(n.selected_lines(), [])

    def test_selected_lines_follow_cursor(self):
        n = nav('b')
        self.assertEqual(n.selected_lines(), [])
        n.left()
        self.assertEqual(n.selected(), 'a')
        self.assertEqual(n.selected_lines(), [' * changed'])


RULE = '─' * 33


class TestFrameLines(unittest.TestCase):

    def test_columns_and_footer(self):
        self.assertEqual(frame_lines(nav('d'), Style()), [
            'parents    tasks      children',
            '~ b        ● a',
            '~ c        ~ b',
            '           ~ c',
            '           [~ d]',
            '           ✓ e',
            RULE,
            'd  may-rerun',
        ])

    def test_reasons(self):
        self.assertEqual(frame_lines(nav('a'), Style()), [
            'parents    tasks      children',
            '           [● a]      ~ b',
            '           ~ b        ~ c',
            '           ~ c',
            '           ~ d',
            '           ✓ e',
            RULE,
            'a  run',
            ' * changed',
        ])

    def test_footer_static_is_the_focus(self):
        self.assertEqual(frame_lines(nav('a'), Style())[-2:],
                         ['a  run', ' * changed'])

    def test_reasons_hidden(self):
        self.assertEqual(frame_lines(nav('a'), Style(), show_reasons=False)[-1],
                         'a  run')

    def test_columns_use_a_third_of_the_width(self):
        got = frame_lines(nav('a'), Style(), width=60)
        self.assertEqual(got[0], 'parents'.ljust(20) + 'tasks'.ljust(20)
                         + 'children')

    def test_color_does_not_change_alignment(self):
        plain = frame_lines(nav('d'), Style())
        colored = frame_lines(nav('d'), Style(color=True))
        strip = lambda line: re.sub(r'\x1b\[[0-9;]*m', '', line)
        self.assertEqual([strip(x).rstrip() for x in colored], plain)


class TestBuildFrame(unittest.TestCase):

    def frame(self, focus, **kw):
        kw.setdefault('width', 60)
        return build_frame(nav(focus), Style(), **kw)

    def texts(self, spans, row):
        return [s.text for s in sorted(spans, key=lambda s: s.x)
                if s.row == row]

    def test_full_screen_pins_footer_and_hints(self):
        spans, total, col_w = self.frame('a', height=12)
        self.assertEqual(total, 12)
        self.assertEqual(col_w, 20)
        rule = 12 - 4 - 1 + 1  # rows below title + reasons line
        self.assertEqual(self.texts(spans, rule)[0][0], '─')
        self.assertEqual(self.texts(spans, 11), [HINTS])

    def test_footer_shows_selected_task(self):
        n = nav('b')
        n.right()  # d
        spans, total, _ = build_frame(n, Style(), 60, 12)
        status = [s for s in spans if s.text.startswith('d  ')]
        self.assertEqual([s.text for s in status], ['d  may-rerun'])
        n.left()
        n.left()  # a, has a reason
        spans, _, _ = build_frame(n, Style(), 60, 12)
        self.assertIn(' * changed', [s.text for s in spans])

    def test_focus_column_lists_all_tasks_focus_in_brackets(self):
        spans, _, _ = self.frame('c', height=12)
        column = [s.text for s in sorted(spans, key=lambda s: s.row)
                  if s.x == 20 and 0 < s.row < 7]
        self.assertEqual(column,
                         ['● a', '~ b', '[~ c]', '~ d', '✓ e'])

    def test_window_follows_cursor_in_focus_column(self):
        names = ['t%02d' % i for i in range(30)]
        empty = {n: [] for n in names}
        n = Navigator(empty, empty, {k: 'run' for k in names}, {}, 't00')
        for _ in range(15):
            n.down()
        spans, _, _ = build_frame(n, Style(), 60, 20, True, True)
        shown = [s.text for s in sorted(spans, key=lambda s: s.row)
                 if s.x == 20 and 0 < s.row <= 11]
        self.assertEqual(shown, ['↑ 11 more']
                         + ['● t%02d' % i for i in range(11, 20)]
                         + ['↓ 10 more'])

    def test_markers_fit_short_screen(self):
        names = ['t%02d' % i for i in range(30)]
        empty = {n: [] for n in names}
        n = Navigator(empty, empty, {k: 'run' for k in names}, {}, 't15')
        spans, total, _ = build_frame(n, Style(), 60, 9, True, True)
        col = [s for s in spans if s.x == 20 and s.row > 0]
        self.assertTrue(all(s.row < 9 - 4 + 1 for s in col))
        self.assertIn('[● t15]', [s.text for s in col])
        self.assertTrue(any('more' in s.text for s in col))

    def test_ascii_markers(self):
        names = ['t%02d' % i for i in range(30)]
        empty = {n: [] for n in names}
        n = Navigator(empty, empty, {k: 'run' for k in names}, {}, 't15')
        spans, _, _ = build_frame(n, Style(ascii_only=True), 60, 20)
        texts = [s.text for s in spans]
        self.assertIn('^ 11 more', texts)
        self.assertIn('v 10 more', texts)

    def test_no_footer(self):
        spans, total, _ = build_frame(nav(None), Style(), 60, footer=False)
        self.assertEqual(total, 6)
        self.assertFalse([s for s in spans if s.row >= 6])

    def test_focus_stays_in_view_when_cursor_is_elsewhere(self):
        names = ['t%02d' % i for i in range(30)]
        parents = {n: [] for n in names}
        parents['t29'] = ['t00']
        children = {n: [] for n in names}
        children['t00'] = ['t29']
        n = Navigator(parents, children, {k: 'run' for k in names}, {}, 't29')
        n.left()  # cursor in parents column
        spans, _, _ = build_frame(n, Style(), 60, 10, True, True)
        self.assertIn('[● t29]', [s.text for s in spans])

    def test_cursor_flag_only_in_active_column(self):
        n = nav('a')
        n.right()
        spans, _, _ = build_frame(n, Style(), 60, 12, cursor=True)
        self.assertEqual([s.text for s in spans if 'cursor' in s.flags],
                         ['~ b'])
        spans, _, _ = self.frame('a', cursor=True, height=12)
        self.assertEqual([s.text for s in spans if 'cursor' in s.flags],
                         ['[● a]'])
        spans, _, _ = self.frame('a', height=12)
        self.assertFalse([s for s in spans if 'cursor' in s.flags])

    def test_children_column_scrolls_with_marker(self):
        many = {'f': [], **{'k%02d' % i: ['f'] for i in range(20)}}
        kids = {'f': sorted(k for k in many if k != 'f')}
        kids.update({k: [] for k in many if k != 'f'})
        states = {k: 'up-to-date' for k in many}
        n = Navigator(many, kids, states, {}, 'f')
        n.right()
        for _ in range(10):
            n.down()
        spans, _, _ = build_frame(n, Style(), 60, 16, True, True)
        shown = [s.text for s in sorted(spans, key=lambda s: s.row)
                 if s.x == 40 and s.row > 0]
        self.assertEqual(shown[0], '↑ 6 more')
        self.assertIn('✓ k10', shown)
        self.assertEqual(shown[-1], '↓ 5 more')
        self.assertEqual(len(shown) - 2, 9)

    def test_column_text_is_cut_to_column(self):
        spans, _, col_w = self.frame('a', height=12)
        cols = [s for s in spans if s.text == '~ b'][0]
        self.assertEqual(cols.maxw, col_w - 1)


class FakeTerminal:
    """scripted keys, records what is written"""

    def __init__(self, keys, size=(60, 12)):
        self.keys = list(keys)
        self._size = size
        self.writes = []
        self.entered = self.left = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *exc):
        self.left = True

    def size(self):
        return self._size

    def write(self, text):
        self.writes.append(text)

    def read_key(self, timeout):
        key = self.keys.pop(0)
        if key == 'resize':
            self._size = (70, 12)
            return None
        return key


def plain(text):
    return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', text)


class TestDraw(unittest.TestCase):

    def test_positions_and_clears(self):
        term = FakeTerminal([])
        draw(term, nav('a'), Style(color=False), True)
        out = term.writes[0]
        self.assertTrue(out.startswith('\x1b[H\x1b[2J'))
        self.assertIn('\x1b[1;1H\x1b[2mparents', out)
        # focus at column 21 (0-based 20), first row
        self.assertIn('\x1b[2;21H\x1b[1;7m[● a]\x1b[0m', out)
        self.assertIn(HINTS, out)

    def test_color_and_no_color(self):
        colored = FakeTerminal([])
        draw(colored, nav('a'), Style(color=True), True)
        self.assertIn('\x1b[31;1;7m[● a]', colored.writes[0])
        mono = FakeTerminal([])
        draw(mono, nav('a'), Style(color=False), True)
        self.assertNotIn('31;', mono.writes[0])
        self.assertIn('\x1b[1;7m[● a]', mono.writes[0])  # cursor still shows

    def test_ascii_hints(self):
        term = FakeTerminal([])
        draw(term, nav('a'), Style(ascii_only=True), True)
        self.assertIn(ASCII_HINTS, term.writes[0])
        self.assertNotIn('←', term.writes[0])

    def test_text_cut_to_screen_and_column(self):
        term = FakeTerminal([], size=(30, 12))
        draw(term, nav('a'), Style(), True)
        text = plain(term.writes[0].replace('\x1b[', '|\x1b['))
        self.assertIn('parents', text)
        # nothing is written outside the screen
        for match in re.finditer(r'\x1b\[(\d+);(\d+)H([^\x1b]*)',
                                 term.writes[0]):
            row, col, body = int(match[1]), int(match[2]), match[3]
            self.assertLessEqual(row, 12)
            self.assertLessEqual(col - 1 + len(body), 29)


class TestRun(unittest.TestCase):

    def run_keys(self, keys, focus='b', reload=None, **kw):
        n = nav(focus)
        term = FakeTerminal(keys, **kw)
        run(n, Style(), reload or (lambda: (STATES, {})), term)
        return n, term

    def test_quit_restores_terminal(self):
        n, term = self.run_keys(['q'])
        self.assertTrue(term.entered and term.left)
        self.assertEqual(len(term.writes), 1)

    def test_esc_quits(self):
        _, term = self.run_keys(['esc'])
        self.assertEqual(len(term.writes), 1)

    def test_keys_navigate(self):
        n, _ = self.run_keys(['right', 'enter', 'left', 'q'])
        self.assertEqual(n.focus, 'd')
        self.assertEqual(n.selected(), 'b')

    def test_r_toggles_reasons(self):
        n, term = self.run_keys(['left', 'r', 'q'], focus='b')
        self.assertIn('changed', term.writes[1])
        self.assertNotIn('changed', term.writes[2])

    def test_R_reloads(self):
        calls = []

        def reload():
            calls.append(1)
            return dict(STATES, b='up-to-date'), {}

        n, term = self.run_keys(['R', 'q'], reload=reload)
        self.assertEqual(calls, [1])
        self.assertEqual(n.states['b'], 'up-to-date')
        self.assertIn('✓ b', plain(term.writes[1]))

    def test_redraw_only_on_key_or_resize(self):
        n = nav('b')
        term = FakeTerminal([None, None, 'q'])
        run(n, Style(), lambda: (STATES, {}), term)
        self.assertEqual(len(term.writes), 1)  # idle polls do not redraw
        term = FakeTerminal([None, 'resize', None, 'q'])
        run(n, Style(), lambda: (STATES, {}), term)
        self.assertEqual(len(term.writes), 2)  # first draw, resize

    def test_restores_terminal_on_error(self):
        term = FakeTerminal(['R'])
        with self.assertRaises(RuntimeError):
            run(nav('b'), Style(), self.boom, term)
        self.assertTrue(term.left)

    @staticmethod
    def boom():
        raise RuntimeError('boom')


class TestParseKey(unittest.TestCase):

    def test_keys(self):
        for data, key in [('\x1b[A', 'up'), ('\x1b[B', 'down'),
                          ('\x1b[C', 'right'), ('\x1b[D', 'left'),
                          ('\x1bOA', 'up'), ('\r', 'enter'),
                          ('\n', 'enter'), ('q', 'q'), ('R', 'R'),
                          ('\x1b', 'esc'), ('\x03', 'esc'),
                          ('\x1b[Z', 'other')]:
            self.assertEqual(parse_key(data), key, data)


class TestOpenTerminal(unittest.TestCase):

    def test_needs_a_terminal(self):
        with self.assertRaises(TuiUnavailable):
            open_terminal(io.StringIO())  # not a tty
