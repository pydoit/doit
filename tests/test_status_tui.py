import unittest

from doit.cmd_status import Style
import re

from doit.status_tui import (
    HINTS, Navigator, build_frame, frame_lines, scroll_start)

# a -> b -> d, a -> c -> d, e alone
PARENTS = {'a': [], 'b': ['a'], 'c': ['a'], 'd': ['b', 'c'], 'e': []}
CHILDREN = {'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': [], 'e': []}
STATES = {'a': 'run', 'b': 'may-rerun', 'c': 'may-rerun', 'd': 'may-rerun',
          'e': 'up-to-date'}


def nav(focus):
    return Navigator(PARENTS, CHILDREN, STATES, {'a': [' * changed']}, focus)


class TestScrollStart(unittest.TestCase):

    def test_fits(self):
        self.assertEqual(scroll_start(3, 2, 5), 0)

    def test_follows_cursor_down_and_up(self):
        self.assertEqual(scroll_start(12, 7, 5, 0), 3)
        self.assertEqual(scroll_start(12, 2, 5, 3), 2)

    def test_cursor_visible_keeps_start(self):
        self.assertEqual(scroll_start(12, 4, 5, 3), 3)

    def test_clamped_to_end(self):
        self.assertEqual(scroll_start(12, 11, 5, 9), 7)


class TestNavigator(unittest.TestCase):

    def test_focus_task_columns(self):
        n = nav('b')
        self.assertEqual(n.column_items('parents'), ['a'])
        self.assertEqual(n.column_items('children'), ['d'])
        self.assertEqual(n.column, 'children')

    def test_up_down_clamped(self):
        n = nav('a')
        n.up()
        self.assertEqual(n.cursor, 0)
        n.down()
        n.down()
        n.down()
        self.assertEqual(n.cursor, 1)
        self.assertEqual(n.selected(), 'c')

    def test_left_right_switch_column_and_reset_cursor(self):
        n = nav('d')
        n.left()
        n.down()
        self.assertEqual(n.selected(), 'c')
        n.right()  # d has no children: stays
        self.assertEqual(n.column, 'parents')
        n.enter()
        self.assertEqual(n.focus, 'c')
        self.assertEqual(n.cursor, 0)

    def test_enter_on_empty_column_is_noop(self):
        n = nav('e')
        n.enter()
        self.assertEqual(n.focus, 'e')

    def test_enter_falls_back_to_other_column(self):
        n = nav('c')
        n.enter()  # children column: d, which has only parents
        self.assertEqual(n.focus, 'd')
        self.assertEqual(n.column, 'parents')

    def test_update_keeps_focus(self):
        n = nav('b')
        n.update(dict(STATES, a='up-to-date', b='up-to-date'), {})
        self.assertEqual(n.focus, 'b')
        self.assertEqual(n.states['b'], 'up-to-date')
        self.assertEqual(n.focus_lines(), [])

    def test_focus_lines(self):
        self.assertEqual(nav('a').focus_lines(), [' * changed'])


RULE = '─' * 33


class TestFrameLines(unittest.TestCase):

    def test_columns_and_footer(self):
        self.assertEqual(frame_lines(nav('d'), Style()), [
            'parents    focus      children',
            '~ b',
            '~ c        [~ d]',
            RULE,
            'd  may-rerun',
        ])

    def test_reasons(self):
        self.assertEqual(frame_lines(nav('a'), Style()), [
            'parents    focus      children',
            '                      ~ b',
            '           [● a]      ~ c',
            RULE,
            'a  run',
            ' * changed',
        ])

    def test_reasons_hidden(self):
        self.assertEqual(frame_lines(nav('a'), Style(), show_reasons=False)[-1],
                         'a  run')

    def test_columns_use_a_third_of_the_width(self):
        got = frame_lines(nav('a'), Style(), width=60)
        self.assertEqual(got[0], 'parents'.ljust(20) + 'focus'.ljust(20)
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

    def test_focus_in_middle_row(self):
        spans, _, _ = self.frame('a', height=13, show_reasons=False)
        focus = [s for s in spans if s.text == '[● a]'][0]
        self.assertEqual(focus.row, 1 + (13 - 4) // 2)

    def test_cursor_flag_only_in_active_column(self):
        spans, _, _ = self.frame('a', cursor=True, height=12)
        self.assertEqual([s.text for s in spans if 'cursor' in s.flags],
                         ['~ b'])
        spans, _, _ = self.frame('a', height=12)
        self.assertFalse([s for s in spans if 'cursor' in s.flags])

    def test_scrolls_long_column(self):
        many = {'f': [], **{'k%02d' % i: ['f'] for i in range(20)}}
        kids = {'f': sorted(k for k in many if k != 'f')}
        kids.update({k: [] for k in many if k != 'f'})
        states = {k: 'up-to-date' for k in many}
        n = Navigator(many, kids, states, {}, 'f')
        for _ in range(15):
            n.down()
        starts = {}
        spans, _, _ = build_frame(n, Style(), 60, 10, True, True, starts)
        shown = [s.text for s in spans if s.x == 40 and s.row > 0
                 and s.row <= 6]
        self.assertIn('✓ k15', shown)
        self.assertEqual(starts['children'], 15 - 6 + 1)

    def test_column_text_is_cut_to_column(self):
        spans, _, col_w = self.frame('a', height=12)
        cols = [s for s in spans if s.text == '~ b'][0]
        self.assertEqual(cols.maxw, col_w - 1)
