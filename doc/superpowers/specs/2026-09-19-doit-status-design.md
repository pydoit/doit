# `doit status` command design

Date: 2026-09-19
Status: draft, revised after first review

## Summary

Add a core sub-command `doit status` that renders the task DAG with up-to-date/stale status,
without persisting any change to doit's state. It generalises the standalone `status.py` script
(prototype from the open-alps project, removed from this repo once phase 1 lands) into doit
itself. It has a static mode (phase 1) and an interactive left-to-right DAG navigator (phase 2).

## Goals

- Show task dependency structure and per-task status as a colored tree.
- Never execute task actions and never persist changes to doit's dependency database.
- Support focusing on one task: its upstream ancestors, optionally its downstream descendants.
- Explain why a task is stale (reasons), reusing what `doit info` already computes.
- Add no runtime dependency (`pyproject.toml` keeps `dependencies = []`).

## Non-goals

- Executing, forgetting, or otherwise changing task state.
- Machine-readable output (`--format json|dot|mermaid`) and CI exit codes. Deferred.
- "What reruns if file X changes" queries. Deferred.
- Windows support for interactive mode. Static mode must work everywhere.
- Side-effect-free status checks. Computing status evaluates `uptodate` entries: callables are
  user code and string entries run as shell commands (`dependency.py`, `subprocess.call`). This
  is the same behavior as `doit list --status` and `doit info`.
- `calc_dep`. File dependencies that a `calc_dep` task computes at run time are not known
  without running it, so they are not part of the graph or the status (same as `list --status`).

## Why a core command

`DoitCmdBase` already provides `self.task_list`, `self.dep_manager`, the configured backend and
`dep_file`, and the configured checker (`doit/cmd_base.py`). The standalone script needs a fake
command object, a `ModuleTaskLoader`, a `sys.path` insert, a `chdir`, and a hardcoded backend
map; a core command needs none of them. `doit list --status` and `doit info` already use
`status_is_ignore()` and `get_status()`, so status semantics match doit's own.

## Graph model

`Status` builds `TaskControl(task_list)` before reading edges. `TaskControl` resolves implicit
edges (a `file_dep` on another task's target) and `wild_dep` patterns onto `task.task_dep` in
place and executes nothing. `List` and `Info` do not build it, so `Status` must. It also gives
the target-to-task map (`TaskControl.targets`) used below.

Edges point from a dependency to its dependent. Each edge has one or both kinds:

- `file`: the dependent has a `file_dep` that is a target of the dependency.
- `order`: the dependent lists the dependency in its explicit `task_dep` (including `wild_dep`
  expansion) or in `setup_tasks`.

Tree direction: roots are sources (tasks with no incoming edge), and a node's children are its
dependents. Children and roots are sorted by name for deterministic output.

### Hidden tasks

Private tasks (name starts with `_`) are hidden without `-p`. Hidden nodes are spliced out: an
edge `a -> _x -> b` becomes `a -> b`. The spliced edge is `file` only if every edge on the path is
`file`; otherwise it is `order`.

### Group tasks and subtasks

A group task is a task with no actions whose `task_dep` contains its own subtasks (tasks with
`subtask_of == group.name`). doit reports such a task as `run` every time
(`has_no_dependencies`), which is noise. `Status` instead gives a group task the aggregate status
of its subtasks (the worst one, in the order `error` > `run` > `may-rerun` > `up-to-date`).

Without `--all`, subtasks are collapsed into their group: every edge to or from a subtask is
redirected to the group node, and the group shows the aggregate status. With `--all`, subtasks
are ordinary nodes, listed flat by name, and the group node keeps its aggregate status.

### Delayed tasks

A task created with `create_after(creates=[...])` is a placeholder until its creator runs
(`loader.py`: the task has a `loader`, no actions and no `file_dep`; its only edge is an `order`
edge to the `executed` task, from `task.py`). Its status and its real edges are unknown. It gets
the state `unknown` with the reason "created at run time (create_after)".

## Status model

Per task, local status comes from doit:

1. `dep_manager.status_is_ignore(task)` is checked first and gives `ignore`.
2. Otherwise `dep_manager.get_status(task, tasks, get_log=True)` gives `up-to-date`, `run`, or
   `error`. `get_log=True` is required: without it `get_status` stops at the first reason, and
   the missing-input rule below needs the full `missing_file_dep` list.

Missing inputs made by other tasks: `get_status` returns `error` when a `file_dep` does not exist
(`dependency.py`, `missing_file_dep`). On a fresh checkout that is true for every task whose
inputs are produced upstream. If every missing `file_dep` is a target of another task, `Status`
reports `run` instead, with the reason "input produced by task X". A `file_dep` that no task
produces stays `error`.

`get_status` is a purely local check. It does not know that an upstream task is about to rewrite
this task's inputs. A derived state covers that:

- `may-rerun`: locally `up-to-date`, and some ancestor reached only through `file` edges has
  status `run` or `error`.

`order` edges do not propagate `may-rerun`. In doit, an explicit `task_dep` controls execution
order only; the dependent reruns only when its own `file_dep` or `uptodate` change. Propagating
over `order` edges would mark tasks below an always-run task (for example a task with no
dependencies) as `~` falsely.

Markers:

| State | Marker | Color |
|---|---|---|
| up-to-date | `✓` | green |
| run | `●` | red |
| may-rerun | `~` | yellow |
| error | `!` | red |
| ignore | `-` | dim |
| unknown | `?` | yellow |

### What "read-only" means

- The command never calls `dep_manager.close()` or the backend's `dump()`. `cmd_base.py`
  documents that commands own the `close()` call, so no task state is ever written.
- `get_status` may change the in-memory DB (on `checker_changed` it calls `remove(task.name)`).
  That change is discarded because nothing dumps.
- Opening the backend may create an empty DB file: `DbmDB` opens with flag `'c'` and `SqliteDB`
  runs `create table if not exists`. Every `DoitCmdBase` command, `list` included, does the same.
  This is accepted.

## Command surface

```
doit status [OPTIONS] [TASK ...]
```

Class `Status(DoitCmdBase)` in `doit/cmd_status.py`, registered in `DOIT_CMDS` in
`doit/doit_cmd.py`.

| Option | Meaning |
|---|---|
| `TASK ...` | Focus tasks. Unknown names raise `InvalidCommand` via `check_tasks_exist`. |
| `-d`, `--downstream` | With `TASK`, also show descendants. Default is upstream plus focus only. |
| `--stale-only` | Hide `✓` and `-` nodes, keeping any node needed to reach a shown node. |
| `--depth N` | Limit tree depth. A cut-off node is shown with `…`. |
| `--reasons` | Under every node that is not `✓` or `-`, print why. |
| `-p`, `--private` | Include tasks starting with `_` (same as `List`). |
| `--all` | Include subtasks as separate nodes (same as `List --all`). |
| `-i`, `--interactive` | Phase 2. Interactive navigator. |

`default_tasks` from `DOIT_CONFIG` is ignored: with no `TASK`, the command always shows the full
graph. Exit code is 0 in phase 1.

## Static output

### No `TASK`

Full tree from the roots. Each task is expanded once only; every other occurrence is omitted, and the
task's line ends with a dim note `(also after: p1, p2)` naming its other parents (`also needed by`
in the upstream tree). This keeps a fan-in-heavy DAG at one line per task (the
open-alps DAG is 27 tasks but 1026 nodes when fully expanded).

The expanded occurrence is the first one, in sorted depth-first order, at the task's shallowest
depth. The shallowest depth is computed first with a breadth-first pass from the roots. So a task
with several parents is expanded under the first parent, by name, that reaches it at minimum
depth. This rule keeps `--depth` correct: a task is never expanded at a deep position that
`--depth` cuts off while a shallower occurrence is omitted. A task that `--depth` cuts off at
its shallowest depth renders as `…` at every occurrence.

### With `TASK`

Focus view, per focus task:

1. The focus task line, with its status. Its reasons always print here (the focus is one task,
   so the output stays short). `--reasons` is not needed for the focus task.
2. Upstream: an inverted tree rooted at the focus task, where a node's children are its
   dependencies. Same expand-once rule.
3. With `-d`: downstream, a tree rooted at the focus task where a node's children are its
   dependents. Same expand-once rule.

Downstream is opt-in because it does not explain the focus task's own status: a stale focus
makes locally up-to-date descendants merely `~`. It does add information about descendants that
are independently stale, hence the flag rather than removal.

Multiple `TASK` arguments render one focus view each, in argument order.

### Reasons

Reasons come from `Info.get_reasons(status.reasons)`, plus:

- For `error`, the message in `status.error_reason` (it is not part of `reasons`).
- For a missing input made upstream, "input produced by task X".
- For `unknown`, "created at run time (create_after)".
- For a group task, the subtasks that set its aggregate status.

### Color and encoding

ANSI escapes and box-drawing characters, written to `self.outstream`. Color is disabled when the
stream is not a TTY or `NO_COLOR` is set. No `rich` dependency.

If the stream encoding cannot encode the markers or box-drawing characters (for example cp1252
on a Windows console, or a redirected stream), the output uses an ASCII set: `+ * ~ ! - ?` for
markers, `|-- `, `` `-- `` for tree lines, and `...` for cut-off nodes.

## Interactive mode (phase 2)

`doit status -i [TASK]` opens a `curses` navigator. The DAG is laid out left to right: parents
in the left column, the focus task in the middle, children in the right column.

```
 parents          focus          children
 ┌ fetch  ●  ─┐
 ├ clean  ✓  ─┼─▶ [build ~] ─┬─▶ report  ~
 └ config ✓  ─┘              └─▶ publish ~
```

Keys:

- `←` / `→`: move the cursor to the parents column / children column.
- `↑` / `↓`: move the cursor within the current column.
- `Enter`: refocus on the task under the cursor.
- `r`: toggle reasons. `R`: reload statuses from disk. `q`: quit.

The focus task's status and reasons show in a footer panel. Columns scroll when longer than the
terminal (a task with 12 parents must stay usable). With no `TASK`, the focus is a virtual
`pipeline` node whose children are the roots.

Snapshot model: the navigator computes all statuses once, then releases the DB handle without
writing. This matters because gdbm takes a lock on open with flag `'c'`, so a long-lived handle
can make a concurrent `doit run` in another terminal fail. Each core backend gets a method that
closes the handle without `dump()` (`DbmDB`: close `_dbm`; `SqliteDB`: close `_conn`; `JsonDB`:
nothing to do). For a plugin backend without this method, the handle stays open. `R` opens a new
`Dependency`, recomputes all statuses, and releases the handle again.

`curses` is stdlib but absent on Windows. In that case `-i` prints "interactive mode
unavailable on this platform" and exits non-zero; static mode is unaffected.

## Structure

- `doit/cmd_status.py`
  - Pure functions over plain data (names, edge lists with kinds, status strings), no doit
    objects: `build_edges`, `splice_hidden`, `collapse_subtasks`, `compute_roots`,
    `resolve_missing_inputs`, `aggregate_group_status`, `compute_may_rerun`,
    `compute_min_depth`, `filter_stale_only`, `render_tree`, `render_focus`. Unit-testable
    without a dodo file.
  - `Status._execute`: builds `TaskControl`, extracts plain data from tasks, computes statuses
    via `dep_manager`, applies filters, writes output.
- `doit/dependency.py` (phase 2): the close-without-dump method on core backends.
- `doit/status_tui.py` (phase 2): the curses front end. It holds only key handling and drawing;
  navigation state (focus, cursor, column contents) lives in a pure class so it is testable
  without a terminal.
- `tests/test_cmd_status.py`: follows `tests/test_cmd_list.py` (use `support.py` helpers).
- Docs: add a `doit status` section to `doc/cmd-other.rst`. The file already has a `status`
  heading for `list --status`, so the new section uses a distinct title and anchor.

## Error handling

- Unknown task: `InvalidCommand`, same message style as `List`.
- `get_status` returns `error` for a task with a missing input that no task produces: shown with
  `!`; the error text appears with `--reasons` and in the focus view.
- No tasks defined: print nothing, exit 0.
- Cycles: doit's `task_dep` graph is acyclic; every walk still guards with a visited set.

## Testing

- Pure functions: table-driven tests on small hand-built DAGs:
  - roots and children/parents maps;
  - edge kinds, including an edge that is both `file` and `order`;
  - splicing through hidden private tasks, and the kind of a spliced edge;
  - subtask collapse and group aggregate status;
  - missing inputs produced upstream becoming `run`, and unproduced ones staying `error`;
  - `may-rerun` through multi-level and diamond graphs, from `run` and `error` ancestors, and not
    across `order` edges;
  - `--stale-only` ancestor retention;
  - `--depth` with a task reached at two depths (expanded at the shallow one, omitted at the deep
    one) and a task cut off everywhere (`…`);
  - expand-once back-references;
  - ASCII fallback rendering.
- Command: run through `Status` with a fake task list and a dep manager in a temp dir, as
  `test_cmd_list.py` does. Assert output with color disabled. Include a `create_after`
  placeholder task.
- Read-only: assert `dep_manager.close`/backend `dump` are never called.
- Phase 2: test the navigation-state class directly, and test that the handle is released after
  loading and reopened on reload. The curses layer gets a smoke test only.

## Phasing

1. Graph and status model, static output, options, tests, docs. Remove `status.py`.
2. `-i` curses front end over the same model, plus the close-without-dump backend method.

Each phase gets its own implementation plan.

## Open questions

None at this time. Earlier questions (group task status, subtask display) are settled in
"Group tasks and subtasks".
