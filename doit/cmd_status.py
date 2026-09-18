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
