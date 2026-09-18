"""command doit status - show task graph with up-to-date/stale status

Read-only: never executes actions, never calls dep_manager.close() or
backend dump(), so no task state is persisted.
"""

from collections import deque, namedtuple

FILE = 'file'
ORDER = 'order'

# file_deps: names of tasks producing one of the task's file_dep
# order_deps: explicit task_dep (incl. wild_dep expansion) and setup_tasks
Node = namedtuple('Node', 'name file_deps order_deps subtask_of delayed')


def build_edges(nodes):
    """edges point from dependency to dependent.

    @return: dict (dep, dependent) -> set of kinds (FILE, ORDER)
    """
    edges = {}

    def add(dep, name, kind):
        if dep != name:
            edges.setdefault((dep, name), set()).add(kind)

    for node in nodes:
        for dep in node.file_deps:
            add(dep, node.name, FILE)
        for dep in node.order_deps:
            add(dep, node.name, ORDER)
    return edges


def collapse_subtasks(edges, group_of):
    """redirect every edge to/from a subtask to its group task.

    @param group_of: dict subtask name -> group name
    """
    result = {}
    for (dep, name), kinds in edges.items():
        dep = group_of.get(dep, dep)
        name = group_of.get(name, name)
        if dep != name:
            result.setdefault((dep, name), set()).update(kinds)
    return result


def splice_hidden(edges, hidden):
    """remove hidden nodes, connecting their dependencies to their dependents.

    A spliced edge is FILE only if both edges on the path are FILE,
    otherwise ORDER.
    """
    edges = {key: set(kinds) for key, kinds in edges.items()}
    for hid in sorted(hidden):
        ins = [(dep, kinds) for (dep, name), kinds in edges.items()
               if name == hid]
        outs = [(name, kinds) for (dep, name), kinds in edges.items()
                if dep == hid]
        for key in [key for key in edges if hid in key]:
            del edges[key]
        for dep, kinds_in in ins:
            for name, kinds_out in outs:
                if dep == name:
                    continue
                both_file = FILE in kinds_in and FILE in kinds_out
                edges.setdefault((dep, name), set()).add(
                    FILE if both_file else ORDER)
    return edges


def build_adjacency(names, edges):
    """@return: (children, parents), dict name -> sorted list of names.
    children of x = dependents of x. parents of x = dependencies of x."""
    children = {name: [] for name in names}
    parents = {name: [] for name in names}
    for dep, name in edges:
        children[dep].append(name)
        parents[name].append(dep)
    for adj in (children, parents):
        for value in adj.values():
            value.sort()
    return children, parents


def compute_roots(names, parents):
    """sources of the graph: names without any dependency"""
    return sorted(name for name in names if not parents[name])


QUIET_STATES = ('up-to-date', 'ignore')
_STALE_STATES = ('run', 'error')
_RANK = {'ignore': -1, 'up-to-date': 0, 'unknown': 1, 'may-rerun': 2,
         'run': 3, 'error': 4}


def aggregate_group_status(statuses):
    """status of a group task: the worst status among its subtasks"""
    return max(statuses, key=_RANK.__getitem__)


def resolve_missing_inputs(status, missing, owners):
    """A missing file_dep that another task produces is not an error: the
    task will run once the producer ran.

    @param status: local status from dep_manager
    @param missing: list of missing file_dep paths
    @param owners: dict path -> name of task producing it
    @return: (status, sorted producer names)
    """
    if status == 'error' and missing and all(f in owners for f in missing):
        return 'run', sorted({owners[f] for f in missing})
    return status, []


def compute_may_rerun(names, edges, states):
    """names of tasks that are locally up-to-date but have an ancestor with
    status run/error, reached only through FILE edges.

    ORDER edges do not propagate: an explicit task_dep only controls order.
    """
    file_parents = {name: [] for name in names}
    for (dep, name), kinds in edges.items():
        if FILE in kinds:
            file_parents[name].append(dep)

    memo = {}

    def stale_above(name):
        if name in memo:
            return memo[name]
        memo[name] = False  # guard against cycles
        memo[name] = any(states[dep] in _STALE_STATES or stale_above(dep)
                         for dep in file_parents[name])
        return memo[name]

    return {name for name in names
            if states[name] == 'up-to-date' and stale_above(name)}


def compute_min_depth(roots, children):
    """shallowest depth of every node reachable from roots (roots = 0)"""
    depth = {}
    queue = deque()
    for root in roots:
        depth[root] = 0
        queue.append(root)
    while queue:
        name = queue.popleft()
        for kid in children.get(name, ()):
            if kid not in depth:
                depth[kid] = depth[name] + 1
                queue.append(kid)
    return depth


def filter_stale_only(roots, children, states):
    """drop nodes in QUIET_STATES unless a kept node is below them.

    @return: (roots, children) with only kept nodes
    """
    keep = {}

    def visit(name):
        if name in keep:
            return keep[name]
        keep[name] = False  # guard against cycles
        below = [visit(kid) for kid in children.get(name, ())]
        keep[name] = states[name] not in QUIET_STATES or any(below)
        return keep[name]

    for root in roots:
        visit(root)
    new_children = {name: [kid for kid in kids if keep.get(kid)]
                    for name, kids in children.items()}
    return [root for root in roots if keep.get(root)], new_children


_MARKERS = {'up-to-date': '✓', 'run': '●', 'may-rerun': '~', 'error': '!',
            'ignore': '-', 'unknown': '?'}
_ASCII_MARKERS = {'up-to-date': '+', 'run': '*', 'may-rerun': '~',
                  'error': '!', 'ignore': '-', 'unknown': '?'}
_COLORS = {'up-to-date': '32', 'run': '31', 'may-rerun': '33', 'error': '31',
           'ignore': '2', 'unknown': '33'}
_DIM = '2'
_GLYPHS = {'branch': '├── ', 'last': '└── ', 'pipe': '│   ',
           'blank': '    ', 'ref': '↑', 'cut': '…'}
_ASCII_GLYPHS = {'branch': '|-- ', 'last': '`-- ', 'pipe': '|   ',
                 'blank': '    ', 'ref': '^', 'cut': '...'}


class Style:
    """colors, markers and tree glyphs"""

    def __init__(self, color=False, ascii_only=False):
        self.color = color
        self.markers = _ASCII_MARKERS if ascii_only else _MARKERS
        self.glyphs = _ASCII_GLYPHS if ascii_only else _GLYPHS

    def _paint(self, text, code):
        if not self.color:
            return text
        return '\033[%sm%s\033[0m' % (code, text)

    def node(self, name, state):
        return self._paint('%s %s' % (self.markers[state], name),
                           _COLORS[state])

    def ref(self, name):
        """back-reference to a task that is expanded elsewhere"""
        return self._paint('%s %s' % (name, self.glyphs['ref']), _DIM)

    def cut(self, name, state):
        """task whose children are hidden by --depth"""
        return '%s %s' % (self.node(name, state), self.glyphs['cut'])


def make_style(stream, environ):
    """color if stream is a TTY and NO_COLOR is unset. ASCII glyphs if the
    stream encoding can not encode the default ones."""
    color = bool(stream.isatty()) and 'NO_COLOR' not in environ
    encoding = getattr(stream, 'encoding', None) or 'utf-8'
    try:
        for text in list(_MARKERS.values()) + list(_GLYPHS.values()):
            text.encode(encoding)
        ascii_only = False
    except (UnicodeEncodeError, LookupError):
        ascii_only = True
    return Style(color, ascii_only)


def render_forest(roots, children, states, style, min_depth, reasons=None,
                  max_depth=None, start_depth=0, indent=''):
    """render trees below `roots` as a list of lines.

    Every task is expanded once: at the first occurrence (sorted DFS) at its
    shallowest depth. Other occurrences are a one-line back-reference.
    A task with children at `max_depth` is shown cut off (at every
    occurrence at its shallowest depth).

    @param min_depth: dict name -> shallowest depth (see compute_min_depth),
                      in the same depth scale as `start_depth`
    @param reasons: dict name -> lines printed verbatim under the task
    """
    reasons = reasons or {}
    lines = []
    expanded = set()
    glyphs = style.glyphs

    def emit(name, depth, lead, child_lead):
        kids = children.get(name, ())
        if depth > min_depth[name] or name in expanded:
            lines.append(lead + style.ref(name))
            return
        if max_depth is not None and depth == max_depth and kids:
            lines.append(lead + style.cut(name, states[name]))
            return
        expanded.add(name)
        lines.append(lead + style.node(name, states[name]))
        for text in reasons.get(name, ()):
            lines.append(child_lead + text)
        for i, kid in enumerate(kids):
            last = i == len(kids) - 1
            emit(kid, depth + 1,
                 child_lead + glyphs['last' if last else 'branch'],
                 child_lead + glyphs['blank' if last else 'pipe'])

    for root in roots:
        emit(root, start_depth, indent, indent)
    return lines


def render_focus(focus, parents, children, states, style, reasons=None,
                 downstream=False, stale_only=False, max_depth=None):
    """focus task, its upstream tree and (optionally) its downstream tree"""
    reasons = reasons or {}
    lines = [style.node(focus, states[focus])]
    lines.extend(reasons.get(focus, ()))
    sections = [('upstream', parents)]
    if downstream:
        sections.append(('downstream', children))
    for label, adj in sections:
        roots = adj[focus]
        if stale_only:
            roots, adj = filter_stale_only(roots, adj, states)
        if not roots:
            continue
        # depth counted from the focus task (depth 0)
        min_depth = {name: depth + 1
                     for name, depth in compute_min_depth(roots, adj).items()}
        lines.append(label + ':')
        lines.extend(render_forest(roots, adj, states, style, min_depth,
                                   reasons, max_depth, start_depth=1,
                                   indent='  '))
    return lines
