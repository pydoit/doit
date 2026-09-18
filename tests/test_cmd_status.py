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
