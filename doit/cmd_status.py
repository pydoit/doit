"""command doit status - show task graph with up-to-date/stale status

Read-only: never executes actions, never calls dep_manager.close() or
backend dump(), so no task state is persisted.
"""

import fnmatch
import os
import shutil
from collections import defaultdict, namedtuple

from .cmd_base import DoitCmdBase, check_tasks_exist
from .cmd_info import Info
from .cmd_list import opt_listall, opt_list_private
from .control import TaskControl
from .exceptions import InvalidCommand
from .status_tui import Navigator, TuiUnavailable, frame_lines, run

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
    """tasks that are locally up-to-date but have an ancestor with status
    run/error, reached only through FILE edges.

    ORDER edges do not propagate: an explicit task_dep only controls order.

    @return: dict task name -> sorted names of its parents (through FILE
             edges) that are stale or have a stale ancestor themselves
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

    return {name: sorted(dep for dep in file_parents[name]
                         if states[dep] in _STALE_STATES or stale_above(dep))
            for name in names
            if states[name] == 'up-to-date' and stale_above(name)}


_MARKERS = {'up-to-date': '✓', 'run': '●', 'may-rerun': '~', 'error': '!',
            'ignore': '-', 'unknown': '?'}
_ASCII_MARKERS = {'up-to-date': '+', 'run': '*', 'may-rerun': '~',
                  'error': '!', 'ignore': '-', 'unknown': '?'}
_COLORS = {'up-to-date': '32', 'run': '31', 'may-rerun': '33', 'error': '31',
           'ignore': '2', 'unknown': '33'}
_DIM = '2'
_GLYPHS = {'rule': '─', 'up': '↑', 'down': '↓'}
_ASCII_GLYPHS = {'rule': '-', 'up': '^', 'down': 'v'}


class Style:
    """colors, markers and glyphs"""

    def __init__(self, color=False, ascii_only=False):
        self.color = color
        self.ascii_only = ascii_only
        self.markers = _ASCII_MARKERS if ascii_only else _MARKERS
        self.glyphs = _ASCII_GLYPHS if ascii_only else _GLYPHS

    def _paint(self, text, code):
        if not self.color:
            return text
        return '\033[%sm%s\033[0m' % (code, text)

    def codes(self, state=None, flags=()):
        """SGR codes: color of a state (only if color is on), plus the
        attributes of the flags dim, bold and cursor (reverse video)"""
        codes = [_COLORS[state]] if state and self.color else []
        codes += [code for flag, code in (('dim', _DIM), ('bold', '1'),
                                          ('cursor', '7')) if flag in flags]
        return ';'.join(codes)

    def span(self, text, state=None, flags=()):
        """text painted with the color of a state, plus dim/bold flags"""
        return self._paint(text, self.codes(state, flags)) \
            if self.color and self.codes(state, flags) else text


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
    'help': "browse the graph in a full-screen navigator, starting at the "
            "TASK (default: all tasks listed, none focused)"
}


class Status(DoitCmdBase):
    doc_purpose = "show task graph with up-to-date status (read-only)"
    doc_usage = "[TASK]"
    doc_description = (
        "Never executes tasks and never saves state.\n"
        "Markers: ✓ up-to-date, ● run, ~ may rerun (an input is produced "
        "by a stale task), ! error, - ignored, ? unknown.")

    cmd_options = (opt_list_private, opt_listall, opt_interactive)

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

    def _execute(self, private=False, subtasks=False, interactive=False,
                 pos_args=None):
        focus_names = list(pos_args or [])
        if interactive and len(focus_names) > 1:
            raise InvalidCommand(
                '`status -i` failed, must select at most *one* task.'
                '\nCheck `{} help status`.'.format(self.bin_name))
        if not interactive and len(focus_names) != 1:
            raise InvalidCommand(
                '`status` failed, must select *one* task, '
                'or use -i to browse.'
                '\nCheck `{} help status`.'.format(self.bin_name))
        tasks = {t.name: t for t in self.task_list}
        if not tasks:
            return 0
        check_tasks_exist(tasks, focus_names)

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
            for name in visible & set(may_rerun):
                lines[name] = [
                    ' * input produced by task %s (%s)'
                    % (dep, 'may-rerun' if dep in may_rerun else local[dep])
                    for dep in may_rerun[name]]
            return states, {name: lines[name] for name in visible
                            if lines.get(name)}

        if not visible:
            return 0
        states, lines = compute()
        style = make_style(self.outstream, os.environ)

        if interactive:
            nav = Navigator(parents, children, states, lines,
                            focus_names[0] if focus_names else None,
                            live=True)
            # snapshot: hold no DB handle while the user navigates
            self.dep_manager.release()

            def reload():
                self.dep_manager.reopen()
                try:
                    return compute()
                finally:
                    self.dep_manager.release()

            try:
                run(nav, style, reload)
            except TuiUnavailable as exception:
                self.outstream.write(
                    'interactive mode unavailable: %s\n' % exception)
                return 1
            return 0

        width = 0  # columns as narrow as their content when piped
        if self.outstream.isatty():
            width = shutil.get_terminal_size().columns
        nav = Navigator(parents, children, states, lines, focus_names[0])
        out = frame_lines(nav, style, width)
        self.outstream.write('\n'.join(out) + '\n')
        return 0
