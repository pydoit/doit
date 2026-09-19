"""full-screen navigator for doit status (interactive mode)

`Navigator` holds all navigation state. `build_frame` lays out the screen and
is shared with the static output. `run` draws it with ANSI escape sequences
(see `status_term` for keys and terminal control).
"""

from collections import namedtuple

from .status_term import CLEAR, TuiUnavailable, open_terminal  # noqa: F401

PARENTS = 'parents'
FOCUS = 'focus'
CHILDREN = 'children'
ORDER = (PARENTS, FOCUS, CHILDREN)  # left to right


TASK_ROWS = 9  # most tasks shown at once in the focus column


def window_start(total, anchor, size):
    """first row of a window of `size` rows around `anchor`, cut off at the
    start and the end of the list"""
    return max(0, min(anchor - size // 2, total - size))


def task_window(total, anchor, available):
    """rows of the focus column: a window of at most `TASK_ROWS` tasks
    around `anchor`, and a marker row above / below it if tasks are hidden

    @param available: rows the column may use
    @return: (first task, number of tasks, hidden above, hidden below)
    """
    size = min(TASK_ROWS, total)
    while True:
        start = window_start(total, anchor, size)
        above, below = start, total - start - size
        if size + bool(above) + bool(below) <= available or size <= 1:
            return start, size, above, below
        size -= 1


class Navigator:
    """focus, cursor and column contents of the DAG navigator.

    The cursor is in one of three columns. The focus column always lists all
    tasks, and the cursor starts on the focus task. Without a focus (`focus`
    None) the cursor starts on the first task and the other columns are empty
    until a task is chosen with `enter`.

    With `live`, the parents and children columns follow the cursor while it
    is in the focus column: the focus (highlighted in brackets) moves with the
    cursor (without a focus, from the first move on).
    """

    def __init__(self, parents, children, states, reasons, focus, live=False):
        self.parents = parents
        self.children = children
        self.live = live
        self.update(states, reasons)
        self._refocus(focus)

    def update(self, states, reasons):
        """replace statuses and reasons (reload), keep the focus"""
        self.states = dict(states)
        self.reasons = dict(reasons)

    def focus_index(self):
        """row of the focus task in the focus column (0 without focus)"""
        if self.focus is None:
            return 0
        return self.column_items(FOCUS).index(self.focus)

    def _refocus(self, name):
        self.focus = name
        self.column = FOCUS
        self.cursor = self.focus_index()

    def column_items(self, column):
        if column == FOCUS:
            return sorted(self.states)
        if self.focus is None:
            return []
        adj = self.parents if column == PARENTS else self.children
        return list(adj[self.focus])

    def items(self):
        return self.column_items(self.column)

    def selected(self):
        """name under the cursor"""
        return self.items()[self.cursor]

    def _move(self, step):
        """cursor to the next column, if it exists and has tasks"""
        index = ORDER.index(self.column) + step
        if 0 <= index < len(ORDER) and self.column_items(ORDER[index]):
            self.column = ORDER[index]
            self.cursor = self.focus_index() if self.column == FOCUS else 0

    def left(self):
        self._move(-1)

    def right(self):
        self._move(1)

    def _follow(self):
        """live: the focus moves with the cursor in the focus column"""
        if self.live and self.column == FOCUS:
            self.focus = self.selected()

    def up(self):
        self.cursor = max(0, self.cursor - 1)
        self._follow()

    def down(self):
        self.cursor = min(len(self.items()) - 1, self.cursor + 1)
        self._follow()

    def enter(self):
        """refocus on the task under the cursor"""
        self._refocus(self.selected())

    def selected_lines(self):
        """reason lines of the selected task"""
        return self.reasons.get(self.selected(), [])


# maxw: text is cut to this width when drawn (None: to the screen edge)
Span = namedtuple('Span', 'row x text state flags maxw')

HINTS = '←→ move  Enter refocus  r reasons  R reload  q quit'
ASCII_HINTS = 'arrows move  Enter refocus  r reasons  R reload  q quit'


def hidden(glyph, count):
    """marker row telling that `count` tasks are not shown"""
    return '%s %d more' % (glyph, count)


def build_frame(nav, style, width=0, height=None, show_reasons=True,
                cursor=False, footer=True):
    """layout of the navigator screen: parents, all tasks (the focus task in
    brackets) and children in columns, then status and reasons of the
    selected task (the focus task unless the cursor moved). Used by the full-screen
    display (`height` = screen rows) and by the static output (`height` None:
    as many rows as needed).

    Columns are a third of `width`, or wider if a name needs it.

    Every column shows at most `TASK_ROWS` tasks: a window around the cursor
    (the focus task, or the first task, when the cursor is in another
    column), with a marker row above / below telling how many tasks are
    hidden.

    @param cursor: mark the selected row (flag 'cursor'), scroll columns
    @param footer: show the status and reasons of the selected task
    @return: (list of Span, number of rows, column width)
    """
    def label(name):
        return '%s %s' % (style.markers[nav.states[name]], name)

    titles = ('parents', 'tasks', 'children')
    columns = [nav.column_items(column) for column in ORDER]
    need = max(max(len(title) for title in titles),
               len(hidden(style.glyphs['down'],
                          max(len(names) for names in columns))),
               *(len(label(n)) + 2 for names in columns for n in names)) + 3
    col_w = max(width // 3, need)
    chosen = nav.selected() if footer else None
    reasons = nav.selected_lines() if footer and show_reasons else []
    anchors = []
    for key in ORDER:
        if cursor and key == nav.column:
            anchors.append(nav.cursor)
        else:
            anchors.append(nav.focus_index() if key == FOCUS else 0)
    if height is None:
        windows = [task_window(len(names), anchor, TASK_ROWS + 2)
                   for names, anchor in zip(columns, anchors)]
        rows = max(size + bool(above) + bool(below)
                   for _, size, above, below in windows) or 1
    else:
        reasons = reasons[:max(0, height // 3)]
        rows = max(1, height - 4 - len(reasons))
        windows = [task_window(len(names), anchor, rows)
                   for names, anchor in zip(columns, anchors)]

    spans = [Span(0, i * col_w, title, None, ('dim',), col_w - 1)
             for i, title in enumerate(titles)]
    for i, (names, (start, size, above, below)) in enumerate(
            zip(columns, windows)):
        selected = nav.cursor if cursor and ORDER[i] == nav.column else -1
        top = 1 + bool(above)
        if above:
            spans.append(Span(1, i * col_w, hidden(style.glyphs['up'], above),
                              None, ('dim',), col_w - 1))
        if below:
            spans.append(Span(top + size, i * col_w,
                              hidden(style.glyphs['down'], below),
                              None, ('dim',), col_w - 1))
        for row, name in enumerate(names[start:start + size]):
            flags = ('cursor',) if start + row == selected else ()
            text = label(name)
            if name == nav.focus:
                flags = ('bold',) + flags
                text = '[%s]' % text
            spans.append(Span(top + row, i * col_w, text, nav.states[name],
                              flags, col_w - 1))

    if not footer:
        return spans, rows + 1, col_w
    rule = rows + 1
    spans.append(Span(rule, 0, style.glyphs['rule'] * (3 * col_w), None,
                      ('dim',), None))
    spans.append(Span(rule + 1, 0, '%s  %s' % (chosen, nav.states[chosen]),
                      nav.states[chosen], ('bold',), None))
    for n, line in enumerate(reasons):
        spans.append(Span(rule + 2 + n, 0, line, None, (), None))
    total = rule + 2 + len(reasons)
    if height is not None:
        hints = ASCII_HINTS if style.ascii_only else HINTS
        spans.append(Span(height - 1, 0, hints, None, ('dim',), None))
        total = height
    return spans, total, col_w


def frame_lines(nav, style, width=0, show_reasons=True, footer=True):
    """the navigator screen as text lines (no terminal needed)"""
    spans, total, _ = build_frame(nav, style, width,
                                  show_reasons=show_reasons, footer=footer)
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


def draw(terminal, nav, style, show_reasons):
    """paint the whole screen in one write"""
    width, height = terminal.size()
    spans, _, _ = build_frame(nav, style, width, height, show_reasons, True)
    out = [CLEAR]
    for span in spans:
        room = width - span.x - 1
        if span.maxw is not None:
            room = min(room, span.maxw)
        if room <= 0 or span.row >= height:
            continue
        codes = style.codes(span.state, span.flags)
        text = span.text[:room]
        if codes:
            text = '\x1b[%sm%s\x1b[0m' % (codes, text)
        out.append('\x1b[%d;%dH%s' % (span.row + 1, span.x + 1, text))
    terminal.write(''.join(out))


def run(nav, style, reload, terminal=None, show_reasons=True):
    """run the navigator until quit.

    @param reload: callable returning new (states, reasons)
    @param terminal: see `status_term.Terminal`, default: the real terminal
    @raise TuiUnavailable: no terminal, or it can not show the screen
    """
    moves = {'left': nav.left, 'right': nav.right, 'up': nav.up,
             'down': nav.down, 'enter': nav.enter}
    with (terminal or open_terminal()) as term:
        last_size = None
        key = 'redraw'
        while key not in ('q', 'esc'):
            if key == 'r':
                show_reasons = not show_reasons
            elif key == 'R':
                nav.update(*reload())
            elif key in moves:
                moves[key]()
            size = term.size()
            if key is not None or size != last_size:
                draw(term, nav, style, show_reasons)
                last_size = size
            key = term.read_key(0.2)
