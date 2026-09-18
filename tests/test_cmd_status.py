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
