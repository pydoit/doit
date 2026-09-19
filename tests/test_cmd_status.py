import types
import unittest
from io import StringIO
from unittest import mock

from doit.cmd_status import (
    Node, Status, Style, make_style, build_edges, collapse_subtasks,
    splice_hidden, build_adjacency, aggregate_group_status,
    resolve_missing_inputs, compute_may_rerun)
from doit.exceptions import InvalidCommand
from doit.status_term import TuiUnavailable
from doit.task import Task
from tests.support import CmdFactory, DepManagerMixin, DependencyFileMixin


class TestBuildEdges(unittest.TestCase):

    def test_kinds(self):
        nodes = [Node('a', [], [], None, False),
                 Node('b', ['a'], [], None, False),
                 Node('c', [], ['a'], None, False),
                 Node('d', ['a'], ['a'], None, False)]
        self.assertEqual(build_edges(nodes), {
            ('a', 'b'): {'file'},
            ('a', 'c'): {'order'},
            ('a', 'd'): {'file', 'order'},
        })

    def test_self_edge_dropped(self):
        nodes = [Node('a', ['a'], ['a'], None, False)]
        self.assertEqual(build_edges(nodes), {})


class TestCollapseSubtasks(unittest.TestCase):

    def test_redirect_to_group(self):
        edges = {('s1', 'g'): {'order'},
                 ('x', 's1'): {'file'},
                 ('s1', 'y'): {'file'}}
        got = collapse_subtasks(edges, {'s1': 'g'})
        self.assertEqual(got, {('x', 'g'): {'file'}, ('g', 'y'): {'file'}})

    def test_kinds_merge(self):
        edges = {('x', 's1'): {'file'}, ('x', 's2'): {'order'}}
        got = collapse_subtasks(edges, {'s1': 'g', 's2': 'g'})
        self.assertEqual(got, {('x', 'g'): {'file', 'order'}})


class TestSpliceHidden(unittest.TestCase):

    def test_all_file(self):
        edges = {('a', '_x'): {'file'}, ('_x', 'b'): {'file'}}
        self.assertEqual(splice_hidden(edges, {'_x'}), {('a', 'b'): {'file'}})

    def test_mixed_is_order(self):
        edges = {('a', '_x'): {'file'}, ('_x', 'b'): {'order'}}
        self.assertEqual(splice_hidden(edges, {'_x'}), {('a', 'b'): {'order'}})

    def test_two_hidden_in_a_row(self):
        edges = {('a', '_x'): {'file'}, ('_x', '_y'): {'file'},
                 ('_y', 'b'): {'file'}}
        got = splice_hidden(edges, {'_x', '_y'})
        self.assertEqual(got, {('a', 'b'): {'file'}})

    def test_input_not_mutated(self):
        edges = {('a', '_x'): {'file'}, ('_x', 'b'): {'file'}}
        splice_hidden(edges, {'_x'})
        self.assertEqual(len(edges), 2)


class TestAdjacency(unittest.TestCase):

    def test_children_parents(self):
        edges = {('a', 'c'): {'file'}, ('a', 'b'): {'order'}}
        children, parents = build_adjacency({'a', 'b', 'c'}, edges)
        self.assertEqual(children, {'a': ['b', 'c'], 'b': [], 'c': []})
        self.assertEqual(parents, {'a': [], 'b': ['a'], 'c': ['a']})

class TestAggregate(unittest.TestCase):

    def test_worst_wins(self):
        self.assertEqual(
            aggregate_group_status(['up-to-date', 'run', 'error']), 'error')
        self.assertEqual(
            aggregate_group_status(['up-to-date', 'run']), 'run')
        self.assertEqual(
            aggregate_group_status(['up-to-date', 'up-to-date']), 'up-to-date')
        self.assertEqual(aggregate_group_status(['ignore', 'ignore']), 'ignore')


class TestResolveMissingInputs(unittest.TestCase):

    def test_all_produced_becomes_run(self):
        owners = {'x': 't1', 'y': 't2'}
        self.assertEqual(resolve_missing_inputs('error', ['x', 'y'], owners),
                         ('run', ['t1', 't2']))

    def test_one_unproduced_stays_error(self):
        self.assertEqual(
            resolve_missing_inputs('error', ['x', 'z'], {'x': 't1'}),
            ('error', []))

    def test_non_error_untouched(self):
        self.assertEqual(resolve_missing_inputs('run', ['x'], {'x': 't1'}),
                         ('run', []))

    def test_error_without_missing_untouched(self):
        self.assertEqual(resolve_missing_inputs('error', [], {}),
                         ('error', []))


class TestMayRerun(unittest.TestCase):

    def test_multi_level(self):
        edges = {('a', 'b'): {'file'}, ('b', 'c'): {'file'}}
        states = {'a': 'run', 'b': 'up-to-date', 'c': 'up-to-date'}
        self.assertEqual(compute_may_rerun(set(states), edges, states),
                         {'b', 'c'})

    def test_diamond(self):
        edges = {('a', 'b'): {'file'}, ('a', 'c'): {'file'},
                 ('b', 'd'): {'file'}, ('c', 'd'): {'file'}}
        states = {n: 'up-to-date' for n in 'bcd'}
        states['a'] = 'run'
        self.assertEqual(compute_may_rerun(set(states), edges, states),
                         {'b', 'c', 'd'})

    def test_error_ancestor(self):
        edges = {('a', 'b'): {'file'}}
        states = {'a': 'error', 'b': 'up-to-date'}
        self.assertEqual(compute_may_rerun(set(states), edges, states), {'b'})

    def test_order_edge_does_not_propagate(self):
        edges = {('a', 'b'): {'order'}, ('b', 'c'): {'file'}}
        states = {'a': 'run', 'b': 'up-to-date', 'c': 'up-to-date'}
        self.assertEqual(compute_may_rerun(set(states), edges, states), set())

    def test_edge_with_both_kinds_propagates(self):
        edges = {('a', 'b'): {'file', 'order'}}
        states = {'a': 'run', 'b': 'up-to-date'}
        self.assertEqual(compute_may_rerun(set(states), edges, states), {'b'})

    def test_only_up_to_date_becomes_may_rerun(self):
        edges = {('a', 'b'): {'file'}}
        states = {'a': 'run', 'b': 'run'}
        self.assertEqual(compute_may_rerun(set(states), edges, states), set())


class FakeStream:
    def __init__(self, encoding=None, tty=False):
        self.encoding = encoding
        self._tty = tty

    def isatty(self):
        return self._tty


class TestStyle(unittest.TestCase):

    def test_markers(self):
        self.assertEqual(Style().markers['run'], '●')
        self.assertEqual(Style().markers['up-to-date'], '✓')
        self.assertEqual(Style(ascii_only=True).markers['run'], '*')
        self.assertEqual(Style(ascii_only=True).markers['up-to-date'], '+')

    def test_span_plain(self):
        self.assertEqual(Style().span('a', 'run', ('bold',)), 'a')

    def test_span_color(self):
        style = Style(color=True)
        self.assertEqual(style.span('a', 'run'), '\033[31ma\033[0m')
        self.assertEqual(style.span('a', 'up-to-date', ('bold',)),
                         '\033[32;1ma\033[0m')

    def test_make_style_not_tty(self):
        self.assertFalse(make_style(FakeStream(), {}).color)

    def test_make_style_tty_color(self):
        self.assertTrue(make_style(FakeStream(tty=True), {}).color)

    def test_make_style_no_color(self):
        self.assertFalse(make_style(FakeStream(tty=True),
                                    {'NO_COLOR': '1'}).color)

    def test_make_style_ascii_encoding(self):
        style = make_style(FakeStream(encoding='ascii'), {})
        self.assertEqual(style.markers['run'], '*')


class StatusTestBase(DependencyFileMixin, DepManagerMixin, unittest.TestCase):

    def status(self, tasks, **kw):
        output = StringIO()
        cmd = CmdFactory(Status, outstream=output, task_list=tasks,
                         dep_manager=self.dep_manager)
        self.assertEqual(cmd._execute(**kw), 0)
        return output.getvalue().splitlines()


class TestCmdStatus(StatusTestBase):
    """no TASK: the screen of the navigator, nothing focused"""

    def test_no_tasks(self):
        self.assertEqual(self.status([]), [])

    def test_unknown_task(self):
        cmd = CmdFactory(Status, outstream=StringIO(),
                         task_list=[Task('a', [''])],
                         dep_manager=self.dep_manager)
        self.assertRaises(InvalidCommand, cmd._execute, pos_args=['nope'])

    def test_lists_all_tasks_nothing_focused(self):
        a = Task('a', [''], targets=['gen/a.out'])
        b = Task('b', [''], file_dep=['gen/a.out'])
        self.assertEqual(self.status([a, b]), [
            'parents    tasks      children',
            '           ● a',
            '           ● b',
        ])

    def test_at_most_nine_tasks_first_nine_without_focus(self):
        tasks = [Task('t%02d' % i, ['']) for i in range(12)]
        got = self.status(tasks)
        self.assertEqual([x.strip() for x in got[1:]],
                         ['● t%02d' % i for i in range(9)] + ['↓ 3 more'])

    def test_at_most_nine_tasks_around_focus(self):
        tasks = [Task('t%02d' % i, ['']) for i in range(20)]
        got = self.status(tasks, pos_args=['t10'])
        rule = [i for i, x in enumerate(got) if x.startswith('──')][0]
        self.assertEqual([x.strip() for x in got[1:rule]],
                         ['↑ 6 more'] + ['● t%02d' % i if i != 10
                                         else '[● t10]'
                                         for i in range(6, 15)]
                         + ['↓ 5 more'])

    def test_window_cut_off_at_start_and_end(self):
        tasks = [Task('t%02d' % i, ['']) for i in range(20)]
        got = self.status(tasks, pos_args=['t01', 't19'])
        first = [x.strip() for x in got[1:11]]
        self.assertEqual(first[0], '● t00')
        self.assertEqual(first[-1], '↓ 11 more')
        self.assertEqual(len(first), 10)  # 9 tasks and the marker
        last = [x.strip() for x in got[-13:-3]]
        self.assertEqual(last[0], '↑ 11 more')
        self.assertEqual(last[-1], '[● t19]')

    def test_no_marker_when_everything_fits(self):
        tasks = [Task('t%02d' % i, ['']) for i in range(9)]
        self.assertFalse([x for x in self.status(tasks) if 'more' in x])

    def test_private_hidden_and_spliced(self):
        a = Task('a', [''], targets=['gen/a.out'])
        x = Task('_x', [''], file_dep=['gen/a.out'], targets=['gen/x.out'])
        b = Task('b', [''], file_dep=['gen/x.out'])
        got = self.status([a, x, b], pos_args=['a'])
        self.assertEqual(got[1], '           [● a]      ● b')
        self.assertEqual(len(got[1:got.index(RULE)]), 2)
        got = self.status([a, x, b], private=True, pos_args=['a'])
        self.assertEqual(got[1], '           ● _x       ● _x')
        self.assertEqual(len(got[1:got.index(RULE)]), 3)

    def test_group_collapsed_and_aggregate(self):
        group = Task('g', None, has_subtask=True)
        group.task_dep = ['g.a', 'g.b']
        ga = Task('g.a', [''], subtask_of='g')
        gb = Task('g.b', [''], subtask_of='g')
        tasks = [group, ga, gb]
        self.assertEqual(self.status(tasks)[1:], ['           ● g'])
        got = self.status(tasks, subtasks=True)
        self.assertEqual(got[1:4], ['           ● g', '           ● g.a',
                                    '           ● g.b'])

    def test_group_reasons_name_subtasks(self):
        group = Task('g', None, has_subtask=True)
        group.task_dep = ['g.a']
        ga = Task('g.a', [''], subtask_of='g')
        got = self.status([group, ga], pos_args=['g'])
        self.assertEqual(got[-2:], ['g  run', ' * subtask g.a: run'])

    def test_delayed_task_is_unknown(self):
        a = Task('a', [''])
        late = Task('late', None,
                    loader=types.SimpleNamespace(task_dep='a'))
        got = self.status([a, late], pos_args=['late'])
        self.assertEqual(got[-2:], ['late  unknown',
                                    ' * created at run time (create_after)'])


RULE = '─' * 33


class TestCmdStatusFocus(StatusTestBase):

    def chain(self):
        a = Task('a', [''], targets=['gen/a.out'])
        b = Task('b', [''], file_dep=['gen/a.out'], targets=['gen/b.out'])
        c = Task('c', [''], file_dep=['gen/b.out'])
        return [a, b, c]

    def test_focus_frame_with_reasons(self):
        self.assertEqual(self.status(self.chain(), pos_args=['b']), [
            'parents    tasks      children',
            '● a        ● a        ● c',
            '           [● b]',
            '           ● c',
            RULE,
            'b  run',
            ' * input produced by task a',
        ])

    def test_multiple_focus_in_argument_order(self):
        got = self.status(self.chain(), pos_args=['c', 'a'])
        focus_rows = [i for i, line in enumerate(got) if '[● ' in line]
        self.assertIn('[● c]', got[focus_rows[0]])
        self.assertIn('[● a]', got[focus_rows[1]])

    def test_focus_private_task_shown_without_flag(self):
        x = Task('_x', [''])
        self.assertIn('[● _x]', self.status([x], pos_args=['_x'])[1])

    def test_focus_subtask_shown_without_all(self):
        group = Task('g', None, has_subtask=True)
        group.task_dep = ['g.a']
        ga = Task('g.a', [''], subtask_of='g')
        self.assertIn('[● g.a]',
                      '\n'.join(self.status([group, ga], pos_args=['g.a'])))


class TestCmdStatusReadOnly(StatusTestBase):

    def test_never_closes_or_dumps(self):
        tasks = [Task('a', [''], targets=['gen/a.out']),
                 Task('b', [''], file_dep=['gen/a.out'])]
        with mock.patch.object(self.dep_manager, 'close') as close, \
                mock.patch.object(self.dep_manager.backend, 'dump') as dump:
            self.status(tasks)
        close.assert_not_called()
        dump.assert_not_called()


class TestCmdStatusInteractive(StatusTestBase):

    def tasks(self):
        return [Task('a', [''], targets=['gen/a.out']),
                Task('b', [''], file_dep=['gen/a.out'])]

    def interactive(self, tasks, **kw):
        """run -i with a fake front end. @return: (nav, calls)"""
        calls = {}

        def fake_run(nav, markers, reload):
            calls['nav'] = nav
            calls['closed_at_run'] = self.dep_manager._closed
            calls['reload'] = reload()
            calls['closed_after_reload'] = self.dep_manager._closed

        output = StringIO()
        cmd = CmdFactory(Status, outstream=output, task_list=tasks,
                         dep_manager=self.dep_manager)
        kw.setdefault('pos_args', ['a'])
        with mock.patch('doit.cmd_status.run', fake_run):
            self.assertEqual(cmd._execute(interactive=True, **kw), 0)
        self.assertEqual(output.getvalue(), '')
        return calls

    def test_handle_released_after_load_and_after_reload(self):
        calls = self.interactive(self.tasks())
        self.assertTrue(calls['closed_at_run'])
        self.assertTrue(calls['closed_after_reload'])

    def test_reload_reopens_and_recomputes(self):
        with mock.patch.object(self.dep_manager, 'reopen',
                               wraps=self.dep_manager.reopen) as reopen:
            calls = self.interactive(self.tasks())
        reopen.assert_called_once_with()
        states, _ = calls['reload']
        self.assertEqual(states, {'a': 'run', 'b': 'run'})

    def test_navigator_starts_at_task(self):
        nav = self.interactive(self.tasks())['nav']
        self.assertEqual(nav.focus, 'a')
        self.assertEqual(nav.column_items('children'), ['b'])

    def test_no_task_lists_all_tasks_in_focus_column(self):
        nav = self.interactive(self.tasks(), pos_args=[])['nav']
        self.assertIsNone(nav.focus)
        self.assertEqual(nav.column_items('focus'), ['a', 'b'])
        self.assertEqual(nav.column, 'focus')

    def test_navigator_focus_task(self):
        nav = self.interactive(self.tasks(), pos_args=['b'])['nav']
        self.assertEqual(nav.focus, 'b')
        self.assertEqual(nav.column_items('parents'), ['a'])


    def test_terminal_unavailable(self):
        output = StringIO()
        cmd = CmdFactory(Status, outstream=output, task_list=self.tasks(),
                         dep_manager=self.dep_manager)
        with mock.patch('doit.cmd_status.run',
                        side_effect=TuiUnavailable('no way')):
            self.assertEqual(cmd._execute(interactive=True, pos_args=['a']),
                             1)
        self.assertEqual(output.getvalue(),
                         'interactive mode unavailable: no way\n')
