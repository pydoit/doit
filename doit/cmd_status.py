"""command doit status - show task graph with up-to-date/stale status

Read-only: never executes actions, never calls dep_manager.close() or
backend dump(), so no task state is persisted.
"""

import fnmatch
import os
import shutil
from collections import defaultdict, deque, namedtuple

from .cmd_base import DoitCmdBase, check_tasks_exist
from .exceptions import InvalidCommand
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
           'blank': '    ', 'cut': '…', 'rule': '─'}
_ASCII_GLYPHS = {'branch': '|-- ', 'last': '`-- ', 'pipe': '|   ',
                 'blank': '    ', 'cut': '...', 'rule': '-'}


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

    def dim(self, text):
        return self._paint(text, _DIM)

    def span(self, text, state=None, flags=()):
        """text painted with the color of a state, plus dim/bold flags"""
        codes = [_COLORS[state]] if state else []
        codes += [code for flag, code in (('dim', _DIM), ('bold', '1'))
                  if flag in flags]
        return self._paint(text, ';'.join(codes)) if codes else text

    def also(self, label, names):
        """note listing the other parents of a task shown once"""
        return self._paint('(%s: %s)' % (label, ', '.join(names)), _DIM)

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
                  max_depth=None, start_depth=0, indent='',
                  also_label='also after'):
    """render trees below `roots` as a list of lines.

    Every task is shown once: at the first occurrence (sorted DFS) at its
    shallowest depth. Its line ends with a note naming its other parents.
    A task with children at `max_depth` is shown cut off.

    @param min_depth: dict name -> shallowest depth (see compute_min_depth),
                      in the same depth scale as `start_depth`
    @param reasons: dict name -> lines printed verbatim under the task
    @param also_label: prefix of the note listing the other parents
    """
    reasons = reasons or {}
    lines = []
    shown = set()
    glyphs = style.glyphs

    # parents of every task reachable from roots, by name
    others = {}
    todo = list(roots)
    seen = set(todo)
    while todo:
        name = todo.pop()
        for kid in children.get(name, ()):
            others.setdefault(kid, set()).add(name)
            if kid not in seen:
                seen.add(kid)
                todo.append(kid)

    def line(name, parent, text):
        extra = sorted(others.get(name, set()) - {parent})
        if extra:
            text += ' ' + style.also(also_label, extra)
        return text

    def emit(name, depth, lead, child_lead, parent):
        shown.add(name)
        kids = children.get(name, ())
        if max_depth is not None and depth == max_depth and kids:
            lines.append(lead + line(name, parent,
                                     style.cut(name, states[name])))
            return
        lines.append(lead + line(name, parent, style.node(name, states[name])))
        for text in reasons.get(name, ()):
            lines.append(child_lead + text)
        # kids shown elsewhere leave no line, so no dangling branch glyph
        # (they are marked as shown when emitted, so filter lazily)
        for i, kid in enumerate(kids):
            rest = [k for k in kids[i:] if wanted(k, depth + 1)]
            if kid not in rest:
                continue
            last = len(rest) == 1
            emit(kid, depth + 1,
                 child_lead + glyphs['last' if last else 'branch'],
                 child_lead + glyphs['blank' if last else 'pipe'], name)

    def wanted(name, depth):
        return depth <= min_depth[name] and name not in shown

    for root in roots:
        if wanted(root, start_depth):
            emit(root, start_depth, indent, indent, None)
    return lines


opt_stale_only = {
    'name': 'stale_only',
    'short': '',
    'long': 'stale-only',
    'type': bool,
    'default': False,
    'help': "hide up-to-date and ignored tasks (keeps tasks needed to "
            "reach a shown one; ignored with TASK)"
}

opt_depth = {
    'name': 'depth',
    'short': '',
    'long': 'depth',
    'type': int,
    'default': None,
    'help': "limit tree depth to N levels below the roots (ignored with "
            "TASK)"
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


opt_interactive = {
    'name': 'interactive',
    'short': 'i',
    'long': 'interactive',
    'type': bool,
    'default': False,
    'help': "browse the graph in a curses navigator, starting at the "
            "first TASK (required)"
}


class Status(DoitCmdBase):
    doc_purpose = "show task graph with up-to-date status (read-only)"
    doc_usage = "[TASK ...]"
    doc_description = (
        "Never executes tasks and never saves state.\n"
        "Markers: ✓ up-to-date, ● run, ~ may rerun (an input is produced "
        "by a stale task), ! error, - ignored, ? unknown.")

    cmd_options = (opt_stale_only, opt_depth, opt_reasons,
                   opt_list_private, opt_listall, opt_interactive)

    def _build_nodes(self, tasks):
        """@return: (nodes, owners), owners: dict target path -> task name"""
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
        return nodes, owners

    def _statuses(self, tasks, owners):
        """@return: (local states, reason lines) by task name"""
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
        return local, lines

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

    def _execute(self, stale_only=False, depth=None,
                 reasons=False, private=False, subtasks=False,
                 interactive=False, pos_args=None):
        focus_names = list(pos_args or [])
        if interactive and not focus_names:
            raise InvalidCommand(
                '`status --interactive` failed, must select a task.'
                '\nCheck `{} help status`.'.format(self.bin_name))
        tasks = {t.name: t for t in self.task_list}
        if not tasks:
            return 0
        check_tasks_exist(tasks, focus_names)
        if interactive:
            try:
                import curses  # noqa: F401
            except ImportError:
                self.outstream.write(
                    "interactive mode unavailable on this platform\n")
                return 1

        nodes, owners = self._build_nodes(tasks)
        names = {node.name for node in nodes}
        edges = build_edges(nodes)

        if not subtasks:
            # a focus subtask stays a node so it can be shown
            group_of = {node.name: node.subtask_of for node in nodes
                        if node.subtask_of in tasks
                        and node.name not in focus_names}
            edges = collapse_subtasks(edges, group_of)
            names -= set(group_of)

        hidden = set()
        if not private:
            hidden = {n for n in names
                      if n.startswith('_') and n not in focus_names}
        visible = names - hidden
        # may-rerun is computed before hidden tasks are spliced out, so a
        # stale private task still marks its dependents
        full_edges = edges
        children, parents = build_adjacency(
            visible, splice_hidden(edges, hidden))

        def compute():
            """@return: (states, reason lines) of the visible tasks"""
            local, lines = self._statuses(tasks, owners)
            may_rerun = compute_may_rerun(names, full_edges, local)
            states = {name: 'may-rerun' if name in may_rerun else local[name]
                      for name in visible}
            return states, {name: lines[name] for name in visible
                            if lines.get(name)}

        states, lines = compute()
        style = make_style(self.outstream, os.environ)
        roots = compute_roots(visible, parents)

        if interactive:
            from . import status_tui
            nav = status_tui.Navigator(parents, children, states, lines,
                                       focus_names[0])
            # snapshot: hold no DB handle while the user navigates
            self.dep_manager.release()

            def reload():
                self.dep_manager.reopen()
                try:
                    return compute()
                finally:
                    self.dep_manager.release()

            status_tui.run(nav, style, reload)
            return 0

        shown = {name: lines[name] for name in lines
                 if name in focus_names
                 or (reasons and states[name] not in QUIET_STATES)}
        out = []
        if focus_names:
            from .status_tui import Navigator, frame_lines
            width = 0  # columns as narrow as their content when piped
            if self.outstream.isatty():
                width = shutil.get_terminal_size().columns
            for focus in focus_names:
                if out:
                    out.append('')
                nav = Navigator(parents, children, states, lines, focus)
                out.extend(frame_lines(nav, style, width))
        else:
            if stale_only:
                roots, children = filter_stale_only(roots, children, states)
            out = render_forest(
                roots, children, states, style,
                compute_min_depth(roots, children), shown, depth)
        if out:
            self.outstream.write('\n'.join(out) + '\n')
        return 0
