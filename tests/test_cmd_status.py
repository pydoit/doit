import unittest

from doit.cmd_status import (
    Node, build_edges, collapse_subtasks, splice_hidden, build_adjacency,
    compute_roots)


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

    def test_children_parents_roots(self):
        edges = {('a', 'c'): {'file'}, ('a', 'b'): {'order'}}
        children, parents = build_adjacency({'a', 'b', 'c'}, edges)
        self.assertEqual(children, {'a': ['b', 'c'], 'b': [], 'c': []})
        self.assertEqual(parents, {'a': [], 'b': ['a'], 'c': ['a']})
        self.assertEqual(compute_roots({'a', 'b', 'c'}, parents), ['a'])

from doit.cmd_status import (
    aggregate_group_status, resolve_missing_inputs, compute_may_rerun,
    compute_min_depth, filter_stale_only)


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


class TestMinDepth(unittest.TestCase):

    def test_shallowest(self):
        children = {'a': ['x'], 'x': ['c'], 'b': ['c'], 'c': []}
        self.assertEqual(compute_min_depth(['a', 'b'], children),
                         {'a': 0, 'b': 0, 'x': 1, 'c': 1})


class TestFilterStaleOnly(unittest.TestCase):

    def test_keeps_path_to_stale_node(self):
        children = {'a': ['b', 'c'], 'b': ['d'], 'c': [], 'd': []}
        states = {'a': 'up-to-date', 'b': 'up-to-date', 'c': 'up-to-date',
                  'd': 'run'}
        roots, kids = filter_stale_only(['a'], children, states)
        self.assertEqual(roots, ['a'])
        self.assertEqual(kids, {'a': ['b'], 'b': ['d'], 'c': [], 'd': []})

    def test_all_quiet_gives_no_roots(self):
        children = {'a': ['b'], 'b': []}
        states = {'a': 'up-to-date', 'b': 'ignore'}
        roots, kids = filter_stale_only(['a'], children, states)
        self.assertEqual(roots, [])

from doit.cmd_status import Style, make_style, render_forest, render_focus


class FakeStream:
    def __init__(self, encoding=None, tty=False):
        self.encoding = encoding
        self._tty = tty

    def isatty(self):
        return self._tty


class TestStyle(unittest.TestCase):

    def test_plain_unicode(self):
        style = Style()
        self.assertEqual(style.node('a', 'run'), '● a')
        self.assertEqual(style.node('a', 'up-to-date'), '✓ a')
        self.assertEqual(style.ref('a'), 'a ↑')
        self.assertEqual(style.cut('a', 'run'), '● a …')

    def test_ascii(self):
        style = Style(ascii_only=True)
        self.assertEqual(style.node('a', 'up-to-date'), '+ a')
        self.assertEqual(style.node('a', 'run'), '* a')
        self.assertEqual(style.ref('a'), 'a ^')
        self.assertEqual(style.cut('a', 'run'), '* a ...')

    def test_color(self):
        style = Style(color=True)
        self.assertEqual(style.node('a', 'run'), '\033[31m● a\033[0m')
        self.assertEqual(style.node('a', 'up-to-date'), '\033[32m✓ a\033[0m')

    def test_make_style_not_tty(self):
        style = make_style(FakeStream(), {})
        self.assertFalse(style.color)
        self.assertEqual(style.node('a', 'run'), '● a')

    def test_make_style_tty_color(self):
        self.assertTrue(make_style(FakeStream(tty=True), {}).color)

    def test_make_style_no_color(self):
        self.assertFalse(make_style(FakeStream(tty=True),
                                    {'NO_COLOR': '1'}).color)

    def test_make_style_ascii_encoding(self):
        style = make_style(FakeStream(encoding='ascii'), {})
        self.assertEqual(style.node('a', 'run'), '* a')


class TestRenderForest(unittest.TestCase):

    def render(self, roots, children, states, **kw):
        md = kw.pop('min_depth', None) or compute_min_depth(roots, children)
        style = kw.pop('style', Style())
        return render_forest(roots, children, states, style, md, **kw)

    def test_chain(self):
        children = {'a': ['b'], 'b': ['c'], 'c': []}
        states = {'a': 'run', 'b': 'may-rerun', 'c': 'may-rerun'}
        self.assertEqual(self.render(['a'], children, states),
                         ['● a', '└── ~ b', '    └── ~ c'])

    def test_siblings_use_pipe(self):
        children = {'a': ['b', 'c'], 'b': ['d'], 'c': [], 'd': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(self.render(['a'], children, states),
                         ['✓ a', '├── ✓ b', '│   └── ✓ d', '└── ✓ c'])

    def test_ascii_lines(self):
        children = {'a': ['b', 'c'], 'b': [], 'c': []}
        states = {n: 'up-to-date' for n in children}
        got = self.render(['a'], children, states,
                          style=Style(ascii_only=True))
        self.assertEqual(got, ['+ a', '|-- + b', '`-- + c'])

    def test_expand_once(self):
        children = {'a': ['c'], 'b': ['c'], 'c': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(self.render(['a', 'b'], children, states),
                         ['✓ a', '└── ✓ c', '✓ b', '└── c ↑'])

    def test_expand_at_shallowest_depth(self):
        children = {'a': ['x'], 'x': ['c'], 'b': ['c'], 'c': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(
            self.render(['a', 'b'], children, states),
            ['✓ a', '└── ✓ x', '    └── c ↑', '✓ b', '└── ✓ c'])

    def test_depth_cut(self):
        children = {'a': ['b'], 'b': ['c'], 'c': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(self.render(['a'], children, states, max_depth=1),
                         ['✓ a', '└── ✓ b …'])

    def test_depth_leaf_at_limit_not_cut(self):
        children = {'a': ['b'], 'b': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(self.render(['a'], children, states, max_depth=1),
                         ['✓ a', '└── ✓ b'])

    def test_cut_at_every_occurrence(self):
        children = {'a': ['c'], 'b': ['c'], 'c': ['d'], 'd': []}
        states = {n: 'up-to-date' for n in children}
        self.assertEqual(
            self.render(['a', 'b'], children, states, max_depth=1),
            ['✓ a', '└── ✓ c …', '✓ b', '└── ✓ c …'])

    def test_reasons(self):
        children = {'a': ['b'], 'b': []}
        states = {'a': 'run', 'b': 'run'}
        reasons = {'a': [' * file missing'], 'b': [' * other']}
        self.assertEqual(
            self.render(['a'], children, states, reasons=reasons),
            ['● a', ' * file missing', '└── ● b', '     * other'])


class TestRenderFocus(unittest.TestCase):

    parents = {'a': [], 'b': ['a'], 'c': ['b']}
    children = {'a': ['b'], 'b': ['c'], 'c': []}
    states = {'a': 'run', 'b': 'may-rerun', 'c': 'may-rerun'}

    def test_upstream_only(self):
        got = render_focus('b', self.parents, self.children, self.states,
                           Style())
        self.assertEqual(got, ['~ b', 'upstream:', '  ● a'])

    def test_downstream(self):
        got = render_focus('b', self.parents, self.children, self.states,
                           Style(), downstream=True)
        self.assertEqual(got, ['~ b', 'upstream:', '  ● a',
                               'downstream:', '  ~ c'])

    def test_focus_reasons_and_no_upstream(self):
        got = render_focus('a', self.parents, self.children, self.states,
                           Style(), reasons={'a': [' * no deps']})
        self.assertEqual(got, ['● a', ' * no deps'])

    def test_stale_only_prunes_upstream(self):
        parents = {'a': [], 'q': [], 'b': ['a', 'q']}
        children = {'a': ['b'], 'q': ['b'], 'b': []}
        states = {'a': 'run', 'q': 'up-to-date', 'b': 'may-rerun'}
        got = render_focus('b', parents, children, states, Style(),
                           stale_only=True)
        self.assertEqual(got, ['~ b', 'upstream:', '  ● a'])

    def test_depth_from_focus(self):
        parents = {'a': [], 'b': ['a'], 'c': ['b']}
        children = {'a': ['b'], 'b': ['c'], 'c': []}
        states = {n: 'up-to-date' for n in parents}
        got = render_focus('c', parents, children, states, Style(),
                           max_depth=1)
        self.assertEqual(got, ['✓ c', 'upstream:', '  ✓ b …'])
