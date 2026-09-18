"""command doit status - show task graph with up-to-date/stale status

Read-only: never executes actions, never calls dep_manager.close() or
backend dump(), so no task state is persisted.
"""

import fnmatch
import os
from collections import defaultdict, deque, namedtuple

from .cmd_base import DoitCmdBase, check_tasks_exist
from .cmd_info import Info
from .cmd_list import opt_listall, opt_list_private
from .control import TaskControl

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


opt_downstream = {
    'name': 'downstream',
    'short': '',  # -d is already --dir
    'long': 'downstream',
    'type': bool,
    'default': False,
    'help': "with TASK, also show tasks that depend on it"
}

opt_stale_only = {
    'name': 'stale_only',
    'short': '',
    'long': 'stale-only',
    'type': bool,
    'default': False,
    'help': "hide up-to-date and ignored tasks (keeps tasks needed to "
            "reach a shown one)"
}

opt_depth = {
    'name': 'depth',
    'short': '',
    'long': 'depth',
    'type': int,
    'default': None,
    'help': "limit tree depth to N levels below the roots (or TASK)"
}

opt_reasons = {
    'name': 'reasons',
    'short': '',
    'long': 'reasons',
    'type': bool,
    'default': False,
    'help': "print why a task is not up-to-date"
}

DELAYED_REASON = ' * created at run time (create_after)'


def _is_delayed(task):
    """placeholder created by create_after: real task not known yet"""
    return task.loader is not None and not task.actions and not task.file_dep


class Status(DoitCmdBase):
    doc_purpose = "show task graph with up-to-date status (read-only)"
    doc_usage = "[TASK ...]"
    doc_description = (
        "Never executes tasks and never saves state.\n"
        "Markers: ✓ up-to-date, ● run, ~ may rerun (an input is produced "
        "by a stale task), ! error, - ignored, ? unknown.")

    cmd_options = (opt_downstream, opt_stale_only, opt_depth, opt_reasons,
                   opt_list_private, opt_listall)

    def _collect(self, tasks):
        """@return: (nodes, local states, reason lines, group of subtask)"""
        # explicit deps must be read before TaskControl adds implicit ones
        explicit = {name: set(task.task_dep) | set(task.setup_tasks)
                    for name, task in tasks.items()}
        owners = TaskControl(self.task_list).targets

        nodes = []
        for name, task in tasks.items():
            wild = {dep for dep in task.task_dep
                    if any(fnmatch.fnmatch(dep, pat)
                           for pat in task.wild_dep)}
            file_deps = sorted({owners[f] for f in task.file_dep
                                if f in owners})
            nodes.append(Node(name, file_deps,
                              sorted(explicit[name] | wild),
                              task.subtask_of, _is_delayed(task)))

        local = {}
        lines = {}
        for name, task in tasks.items():
            local[name], lines[name] = self._task_status(task, tasks, owners)

        subs = defaultdict(dict)
        for name, task in tasks.items():
            if task.subtask_of in tasks:
                subs[task.subtask_of][name] = local[name]
        for group, sub_states in subs.items():
            worst = aggregate_group_status(sub_states.values())
            local[group] = worst
            lines[group] = [
                ' * subtask %s: %s' % (sub, state)
                for sub, state in sorted(sub_states.items())
                if state == worst and state not in QUIET_STATES]
        return nodes, local, lines

    def _task_status(self, task, tasks, owners):
        """@return: (status, list of reason lines)"""
        if _is_delayed(task):
            return 'unknown', [DELAYED_REASON]
        if self.dep_manager.status_is_ignore(task):
            return 'ignore', []
        result = self.dep_manager.get_status(task, tasks, get_log=True)
        state = result.status
        lines = Info.get_reasons(result.reasons).splitlines()
        if state == 'error':
            missing = result.reasons.get('missing_file_dep', [])
            state, producers = resolve_missing_inputs(state, missing, owners)
            if state == 'run':
                return state, [' * input produced by task %s' % name
                               for name in producers]
            if result.error_reason:
                lines.append(' * %s' % result.error_reason)
        return state, lines

    def _execute(self, downstream=False, stale_only=False, depth=None,
                 reasons=False, private=False, subtasks=False,
                 pos_args=None):
        tasks = {t.name: t for t in self.task_list}
        if not tasks:
            return 0
        focus_names = list(pos_args or [])
        check_tasks_exist(tasks, focus_names)

        nodes, local, lines = self._collect(tasks)
        names = {node.name for node in nodes}
        edges = build_edges(nodes)

        if not subtasks:
            # a focus subtask stays a node so it can be shown
            group_of = {node.name: node.subtask_of for node in nodes
                        if node.subtask_of in tasks
                        and node.name not in focus_names}
            edges = collapse_subtasks(edges, group_of)
            names -= set(group_of)

        # may-rerun is computed before hidden tasks are spliced out, so a
        # stale private task still marks its dependents
        may_rerun = compute_may_rerun(names, edges, local)
        states = {name: 'may-rerun' if name in may_rerun else local[name]
                  for name in names}

        hidden = set()
        if not private:
            hidden = {n for n in names
                      if n.startswith('_') and n not in focus_names}
        edges = splice_hidden(edges, hidden)
        visible = names - hidden
        children, parents = build_adjacency(visible, edges)

        shown = {name: lines[name] for name in visible
                 if lines.get(name)
                 and (name in focus_names
                      or (reasons and states[name] not in QUIET_STATES))}

        style = make_style(self.outstream, os.environ)
        out = []
        if focus_names:
            for focus in focus_names:
                if out:
                    out.append('')
                out.extend(render_focus(
                    focus, parents, children, states, style, shown,
                    downstream=downstream, stale_only=stale_only,
                    max_depth=depth))
        else:
            roots = compute_roots(visible, parents)
            if stale_only:
                roots, children = filter_stale_only(roots, children, states)
            out = render_forest(
                roots, children, states, style,
                compute_min_depth(roots, children), shown, depth)
        if out:
            self.outstream.write('\n'.join(out) + '\n')
        return 0
