import unittest

from doit.status_tui import Navigator, PIPELINE, scroll_start

# a -> b -> d, a -> c -> d, e alone
PARENTS = {'a': [], 'b': ['a'], 'c': ['a'], 'd': ['b', 'c'], 'e': []}
CHILDREN = {'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': [], 'e': []}
STATES = {'a': 'run', 'b': 'may-rerun', 'c': 'may-rerun', 'd': 'may-rerun',
          'e': 'up-to-date'}


def nav(focus=None):
    return Navigator(PARENTS, CHILDREN, ['a', 'e'], STATES,
                     {'a': [' * changed']}, focus)


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

    def test_pipeline_focus_children_are_roots(self):
        n = nav()
        self.assertEqual(n.focus, PIPELINE)
        self.assertEqual(n.column_items('parents'), [])
        self.assertEqual(n.column_items('children'), ['a', 'e'])
        self.assertEqual(n.states[PIPELINE], 'run')

    def test_root_has_pipeline_as_parent(self):
        n = nav()
        n.enter()
        self.assertEqual(n.focus, 'a')
        self.assertEqual(n.column_items('parents'), [PIPELINE])
        n.left()
        n.enter()
        self.assertEqual(n.focus, PIPELINE)

    def test_task_focus_has_no_pipeline_parent(self):
        self.assertEqual(nav('a').column_items('parents'), [])

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
