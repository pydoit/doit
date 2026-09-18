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

    The cursor is in one of three columns; the focus column has a single
    task and is selected by default.
    """

    def __init__(self, parents, children, states, reasons, focus):
        self.parents = parents
        self.children = children
        self.update(states, reasons)
        self._refocus(focus)

    def update(self, states, reasons):
        """replace statuses and reasons (reload), keep the focus"""
        self.states = dict(states)
        self.reasons = dict(reasons)

    def _refocus(self, name):
        self.focus = name
        self.column = FOCUS
        self.cursor = 0

    def column_items(self, column):
        if column == FOCUS:
            return [self.focus]
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
            self.cursor = 0

    def left(self):
        self._move(-1)

    def right(self):
        self._move(1)

    def up(self):
        self.cursor = max(0, self.cursor - 1)

    def down(self):
        self.cursor = min(len(self.items()) - 1, self.cursor + 1)

    def enter(self):
        """refocus on the task under the cursor"""
        self._refocus(self.selected())

    def selected_lines(self):
        """reason lines of the selected task"""
        return self.reasons.get(self.selected(), [])


# maxw: text is cut to this width when drawn (None: to the screen edge)
Span = namedtuple('Span', 'row x text state flags maxw')

HINTS = '←→↑↓ move  Enter refocus  r reasons  R reload  q quit'
ASCII_HINTS = 'arrows move  Enter refocus  r reasons  R reload  q quit'


def build_frame(nav, style, width=0, height=None, show_reasons=True,
                cursor=False, starts=None):
    """layout of the navigator screen: parents, focus and children in
    columns, then status and reasons of the selected task (the focus task
    unless the cursor moved). Used by the full-screen
    display (`height` = screen rows) and by the static output (`height` None:
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
    chosen = nav.selected()
    reasons = nav.selected_lines() if show_reasons else []
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
            flags = ('bold', 'cursor') if cursor and nav.column == FOCUS \
                else ('bold',)
            spans.append(Span(1 + rows // 2, col_w, '[%s]' % label(nav.focus),
                              nav.states[nav.focus], flags, col_w - 1))
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


def frame_lines(nav, style, width=0, show_reasons=True):
    """the navigator screen as text lines (no terminal needed)"""
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


def draw(terminal, nav, style, show_reasons, starts):
    """paint the whole screen in one write"""
    width, height = terminal.size()
    spans, _, _ = build_frame(nav, style, width, height, show_reasons, True,
                              starts)
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
    starts = {}
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
                draw(term, nav, style, show_reasons, starts)
                last_size = size
            key = term.read_key(0.2)
