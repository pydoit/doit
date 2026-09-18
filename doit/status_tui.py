"""curses navigator for doit status (interactive mode)

`Navigator` holds all navigation state and is independent of curses.
`run` is the thin curses front end.
"""

from collections import namedtuple

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
    """focus, cursor and column contents of the DAG navigator"""

    def __init__(self, parents, children, states, reasons, focus):
        self.parents = parents
        self.children = children
        self.column = CHILDREN
        self.cursor = 0
        self.update(states, reasons)
        self.focus = focus
        self._fix_column()

    def update(self, states, reasons):
        """replace statuses and reasons (reload), keep the focus"""
        self.states = dict(states)
        self.reasons = dict(reasons)

    def column_items(self, column):
        adj = self.parents if column == PARENTS else self.children
        return list(adj[self.focus])

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


# maxw: text is cut to this width when drawn (None: to the screen edge)
Span = namedtuple('Span', 'row x text state flags maxw')

HINTS = ('←→ column  ↑↓ move  Enter focus  r reasons  R reload  q quit')


def build_frame(nav, style, width=0, height=None, show_reasons=True,
                cursor=False, starts=None):
    """layout of the navigator screen: parents, focus and children in
    columns, then status and reasons of the focus task. Used by the curses
    screen (`height` = screen rows) and by the static output (`height` None:
    as many rows as needed).

    Columns are a third of `width`, or wider if a name needs it.

    @param cursor: mark the selected row (flag 'cursor'), scroll columns
    @param starts: dict column -> first visible row, updated when scrolling
    @return: (list of Span, number of rows, column width)
    """
    def label(name):
        return '%s %s' % (style.markers[nav.states[name]], name)

    titles = ('parents', 'focus', 'children')
    columns = (nav.column_items(PARENTS), [nav.focus],
               nav.column_items(CHILDREN))
    need = max(max(len(title) for title in titles),
               *(len(label(n)) + 2 for names in columns for n in names)) + 3
    col_w = max(width // 3, need)
    reasons = nav.focus_lines() if show_reasons else []
    if height is None:
        rows = max(len(columns[0]), len(columns[2]), 1)
    else:
        reasons = reasons[:max(0, height // 3)]
        rows = max(1, height - 4 - len(reasons))

    spans = [Span(0, i * col_w, title, None, ('dim',), col_w - 1)
             for i, title in enumerate(titles)]
    starts = {} if starts is None else starts
    for i, names in enumerate(columns):
        if i == 1:
            spans.append(Span(1 + rows // 2, col_w, '[%s]' % label(nav.focus),
                              nav.states[nav.focus], ('bold',), col_w - 1))
            continue
        key = PARENTS if i == 0 else CHILDREN
        selected = nav.cursor if cursor and key == nav.column else -1
        start = 0
        if height is not None:
            start = scroll_start(len(names), max(selected, 0), rows,
                                 starts.get(key, 0))
            starts[key] = start
        for row, name in enumerate(names[start:start + rows]):
            flags = ('cursor',) if start + row == selected else ()
            spans.append(Span(1 + row, i * col_w, label(name),
                              nav.states[name], flags, col_w - 1))

    rule = rows + 1
    spans.append(Span(rule, 0, style.glyphs['rule'] * (3 * col_w), None,
                      ('dim',), None))
    spans.append(Span(rule + 1, 0, '%s  %s' % (nav.focus,
                                               nav.states[nav.focus]),
                      nav.states[nav.focus], ('bold',), None))
    for n, line in enumerate(reasons):
        spans.append(Span(rule + 2 + n, 0, line, None, (), None))
    total = rule + 2 + len(reasons)
    if height is not None:
        spans.append(Span(height - 1, 0, HINTS, None, ('dim',), None))
        total = height
    return spans, total, col_w


def frame_lines(nav, style, width=0, show_reasons=True):
    """the navigator screen as text lines (no curses needed)"""
    spans, total, _ = build_frame(nav, style, width,
                                  show_reasons=show_reasons)
    lines = []
    for row in range(total):
        line = ''
        used = 0
        for span in sorted((s for s in spans if s.row == row),
                           key=lambda s: s.x):
            line += ' ' * (span.x - used) + style.span(
                span.text, span.state, span.flags)
            used = span.x + len(span.text)
        lines.append(line)
    return lines


def draw(stdscr, curses, nav, style, show_reasons, pairs, starts):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    spans, _, col_w = build_frame(nav, style, width, height, show_reasons,
                                  True, starts)
    for span in spans:
        attr = curses.color_pair(pairs.get(span.state, 0))
        for flag, extra in (('dim', curses.A_DIM), ('bold', curses.A_BOLD),
                            ('cursor', curses.A_REVERSE)):
            if flag in span.flags:
                attr |= extra
        room = width - span.x - 1
        if span.maxw is not None:
            room = min(room, span.maxw)
        try:
            stdscr.addnstr(span.row, span.x, span.text, max(0, room), attr)
        except curses.error:  # pragma: no cover
            pass
    stdscr.refresh()


def run(nav, style, reload, show_reasons=True):
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
            draw(stdscr, curses, nav, style, reasons_on, pairs, starts)
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
