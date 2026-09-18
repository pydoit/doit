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
        n.up()
        self.assertEqual(n.selected(), 'a')

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
        self.assertEqual((n.column, n.cursor, n.selected()), ('focus', 0, 'c'))

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

    def test_footer_static_is_the_focus(self):
        self.assertEqual(frame_lines(nav('a'), Style())[-2:],
                         ['a  run', ' * changed'])

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

    def test_focus_in_middle_row(self):
        spans, _, _ = self.frame('a', height=13, show_reasons=False)
        focus = [s for s in spans if s.text == '[● a]'][0]
        self.assertEqual(focus.row, 1 + (13 - 4) // 2)

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

    def test_scrolls_long_column(self):
        many = {'f': [], **{'k%02d' % i: ['f'] for i in range(20)}}
        kids = {'f': sorted(k for k in many if k != 'f')}
        kids.update({k: [] for k in many if k != 'f'})
        states = {k: 'up-to-date' for k in many}
        n = Navigator(many, kids, states, {}, 'f')
        n.right()
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
