"""curses navigator for doit status (interactive mode)

`Navigator` holds all navigation state and is independent of curses.
`run` is the thin curses front end.
"""

from .cmd_status import aggregate_group_status

PIPELINE = 'pipeline'
PARENTS = 'parents'
CHILDREN = 'children'


def scroll_start(total, cursor, height, start=0):
    """first visible row of a column so that `cursor` stays visible

    @param start: first visible row before the move
    """
    if total <= height:
        return 0
    if cursor < start:
        start = cursor
    elif cursor >= start + height:
        start = cursor - height + 1
    return max(0, min(start, total - height))


class Navigator:
    """focus, cursor and column contents of the DAG navigator.

    Without a focus task, the focus is a virtual `pipeline` node: its
    children are the roots and it is the only parent of every root.
    """

    def __init__(self, parents, children, roots, states, reasons, focus=None):
        self.parents = parents
        self.children = children
        self.roots = list(roots)
        self.virtual = focus is None
        self.column = CHILDREN
        self.cursor = 0
        self.reasons = {}
        self.states = {}
        self.update(states, reasons)
        self.focus = PIPELINE if focus is None else focus
        self._fix_column()

    def update(self, states, reasons):
        """replace statuses and reasons (reload), keep the focus"""
        self.states = dict(states)
        self.reasons = dict(reasons)
        if self.virtual:
            self.states[PIPELINE] = (
                aggregate_group_status([states[r] for r in self.roots])
                if self.roots else 'up-to-date')

    def column_items(self, column):
        if column == PARENTS:
            if self.focus == PIPELINE:
                return []
            found = list(self.parents.get(self.focus, ()))
            if self.virtual and self.focus in self.roots:
                found.append(PIPELINE)
            return found
        if self.focus == PIPELINE:
            return list(self.roots)
        return list(self.children.get(self.focus, ()))

    def items(self):
        return self.column_items(self.column)

    def selected(self):
        """name under the cursor, None if the column is empty"""
        items = self.items()
        return items[self.cursor] if items else None

    def _fix_column(self):
        if not self.items():
            other = PARENTS if self.column == CHILDREN else CHILDREN
            if self.column_items(other):
                self.column = other
        self.cursor = 0

    def left(self):
        if self.column_items(PARENTS):
            self.column = PARENTS
            self.cursor = 0

    def right(self):
        if self.column_items(CHILDREN):
            self.column = CHILDREN
            self.cursor = 0

    def up(self):
        self.cursor = max(0, self.cursor - 1)

    def down(self):
        self.cursor = min(max(0, len(self.items()) - 1), self.cursor + 1)

    def enter(self):
        """refocus on the task under the cursor"""
        name = self.selected()
        if name is None:
            return
        self.focus = name
        self._fix_column()

    def focus_lines(self):
        """reason lines of the focus task"""
        return self.reasons.get(self.focus, [])


def _label(nav, name, markers):
    return '%s %s' % (markers[nav.states[name]], name)


def draw(stdscr, curses, nav, markers, show_reasons, pairs, starts):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    col_w = max(10, width // 3)
    footer = 3
    if show_reasons:
        footer += min(len(nav.focus_lines()), max(0, height // 3))
    rows = max(1, height - footer)

    def put(y, x, text, attr=0):
        try:
            stdscr.addnstr(y, x, text, max(0, min(col_w - 1, width - x - 1)),
                           attr)
        except curses.error:  # pragma: no cover
            pass

    def state_attr(name):
        return curses.color_pair(pairs.get(nav.states[name], 0))

    for i, (title, column) in enumerate(
            (('parents', PARENTS), ('focus', None), ('children', CHILDREN))):
        put(0, i * col_w, title, curses.A_DIM)
        if column is None:
            put(rows // 2 + 1, i * col_w,
                '[%s]' % _label(nav, nav.focus, markers),
                curses.A_BOLD | state_attr(nav.focus))
            continue
        items = nav.column_items(column)
        active = column == nav.column
        cursor = nav.cursor if active else -1
        start = scroll_start(len(items), max(cursor, 0), rows,
                             starts.get(column, 0))
        starts[column] = start
        for row, name in enumerate(items[start:start + rows]):
            attr = state_attr(name)
            if start + row == cursor:
                attr |= curses.A_REVERSE
            put(row + 1, i * col_w, _label(nav, name, markers), attr)

    y = height - footer
    stdscr.hline(y, 0, curses.ACS_HLINE, width)
    put(y + 1, 0, '%s  %s' % (nav.focus, nav.states[nav.focus]),
        curses.A_BOLD | state_attr(nav.focus))
    if show_reasons:
        for n, line in enumerate(nav.focus_lines()[:height - y - 3]):
            put(y + 2 + n, 0, line)
    put(height - 1, 0, '←→ column  ↑↓ move  Enter focus  r reasons  '
        'R reload  q quit', curses.A_DIM)
    stdscr.refresh()


def run(nav, markers, reload, show_reasons=True):
    """run the navigator until quit.

    @param reload: callable returning new (states, reasons)
    """
    import curses

    def main(stdscr):
        curses.curs_set(0)
        pairs = {}
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            for i, (state, color) in enumerate(
                    (('up-to-date', curses.COLOR_GREEN),
                     ('run', curses.COLOR_RED),
                     ('may-rerun', curses.COLOR_YELLOW),
                     ('error', curses.COLOR_RED),
                     ('unknown', curses.COLOR_YELLOW)), 1):
                curses.init_pair(i, color, -1)
                pairs[state] = i
        starts = {}
        reasons_on = show_reasons
        keys = {curses.KEY_LEFT: nav.left, curses.KEY_RIGHT: nav.right,
                curses.KEY_UP: nav.up, curses.KEY_DOWN: nav.down,
                curses.KEY_ENTER: nav.enter, 10: nav.enter, 13: nav.enter}
        while True:
            draw(stdscr, curses, nav, markers, reasons_on, pairs, starts)
            key = stdscr.getch()
            if key in (ord('q'), 27):
                return
            if key == ord('r'):
                reasons_on = not reasons_on
            elif key == ord('R'):
                nav.update(*reload())
            elif key in keys:
                keys[key]()

    curses.wrapper(main)
