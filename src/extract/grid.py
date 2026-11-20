"""Rebuild the State/UT rows of one annexure page from character positions.

The text-line reading of pdftext.py (one line per baseline) is not enough for
these tables: CTD wraps long names around their values ("Andhra" / values /
"Pradesh"), and in several tables it stacks a cell's count above its
percentage, so that one table row is printed over three baselines with some
of its counts on the line above the name (ITR 2019 Annexure 1.2; ITR 2020
Annexure 3.3, Uttar Pradesh). On ITR 2020 PDF p. 211 the West Bengal and India
rows overlap. So each page is read here as positioned tokens:

1. Characters are grouped by baseline into lines (v = position across rows)
   and, along the line, into tokens with their extent u (position along the
   row). Rotated pages (text turned 90 degrees counter-clockwise) and upright
   pages are handled alike, through (u, v).
2. A line's leading text tokens are a name fragment; the rest must be values.
   Fragments are joined into printed names with the crosswalk (crosswalk.py):
   a fragment continues the current name while the joined text is the start
   of a printed name of that data year.
3. A count followed on its line by a percentage is one cell. A percentage
   printed on a line of its own is joined to the bare count above it (within
   one row pitch)
   in the same column (the stacked layout); otherwise it is a cell with a blank
   count.
4. A cell belongs to the row whose name is on its line. A cell on a line
   without a name belongs to the row whose centre (the middle of its name
   lines) is nearest to the cell's centre; it must be clearly nearer to that
   row than to any other, and within 0.6 row pitches.
5. Columns: on every page, the rows that print all `ncells` cells give each
   column's position (the median token centre). A row with fewer cells (a
   blank printed as nothing) has each cell placed in the nearest column; a
   cell may not be nearer another column than its own, in any row.

Lines and cells before the first row or after the last row (titles, headers,
footnotes, page numbers) are ignored; anything else that cannot be placed
raises ValueError.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from src.extract import annex, crosswalk, pdftext

LINE_TOL = 1.0  # points: chars whose baselines differ by more are on different lines
WORD_GAP = 0.15  # x font size: a larger gap between chars on a line splits a word
INLINE_GAP = 1.5  # x font size: max gap between a count and its percentage on one line
STACK_DV = 1.0  # x row pitch: max baseline distance between a stacked count and its percentage
MAX_ROW_DIST = 0.6  # x row pitch: max distance of a nameless cell from its row's centre
NEAR_RATIO = 0.7  # nearest row distance / second-nearest row distance must not exceed this


@dataclass
class Token:
    text: str
    u0: float
    u1: float
    v: float
    size: float

    @property
    def uc(self) -> float:
        return (self.u0 + self.u1) / 2


@dataclass
class Line:
    v: float
    tokens: list[Token]
    name: list[Token] = field(default_factory=list)
    values: list[Token] = field(default_factory=list)
    text_after_values: bool = False  # a text token after the first value
    row: int | None = None  # index of the row whose name is on this line

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.tokens)


@dataclass
class PCell:
    count: Token | None  # the count (or blank marker); None for a lone percentage
    pct: Token | None
    blank: bool  # a blank marker or a lone percentage
    line: int  # index of the line of the count (or of the lone percentage)
    pct_line: int | None = None
    row: int | None = None

    @property
    def tok(self) -> Token:
        return self.count if self.count is not None else self.pct  # type: ignore[return-value]

    @property
    def uc(self) -> float:
        if self.count is not None and self.pct is not None and self.pct_line == self.line:
            return (self.count.u0 + self.pct.u1) / 2
        return self.tok.uc

    def cell(self) -> annex.Cell:
        n = None if self.blank or self.count is None else self.count.text
        pct = self.pct.text if self.pct is not None else None
        raw = " ".join(t.text for t in (self.count, self.pct) if t is not None)
        return annex.Cell(n, pct, raw)


@dataclass
class Row:
    name: str
    lines: list[int]
    vc: float = 0.0
    cells: list[PCell] = field(default_factory=list)


@dataclass
class PageRows:
    """Rows of one page: printed name -> cells (length ncells, None = not printed)."""
    rows: dict[str, list[annex.Cell | None]]
    national: list[annex.Cell | None] | None
    raw_names: dict[str, str]  # canonical printed name (or "India") -> name as printed
    ignored: list[str]  # text of lines ignored as header or footer


# ---- characters -> lines -> tokens ---------------------------------------------

def _uv(c: dict, rotated: bool, height: float) -> tuple[float, float, float]:
    """(u0, u1, v) of a character."""
    if rotated:
        return height - c["bottom"], height - c["top"], c["matrix"][4]
    return c["x0"], c["x1"], height - c["matrix"][5]


def lines_of(chars: list[dict], width: float, height: float,
             region: tuple[float, float] | None = None) -> list[Line]:
    """Lines of positioned tokens, in reading order.

    `region` keeps only the characters whose centre lies within that fraction of
    the page width (TBAR 2022 prints two tables side by side on one PDF page).
    """
    rotated = pdftext._is_rotated(chars)
    sel = [c for c in chars if c["upright"] != rotated]
    if region is not None:
        lo, hi = region[0] * width, region[1] * width
        sel = [c for c in sel if lo <= (c["x0"] + c["x1"]) / 2 <= hi]
    pts = sorted(((*_uv(c, rotated, height), c) for c in sel), key=lambda t: (t[2], t[0]))
    groups: list[list[tuple]] = []
    for p in pts:
        if groups and abs(p[2] - groups[-1][0][2]) <= LINE_TOL:
            groups[-1].append(p)
        else:
            groups.append([p])
    out: list[Line] = []
    for g in groups:
        g.sort(key=lambda t: t[0])
        words: list[list[tuple]] = []
        for p in g:
            c = p[3]
            if not c["text"].strip():
                words.append([])
                continue
            if words and words[-1] and p[0] - words[-1][-1][1] <= WORD_GAP * c["size"]:
                words[-1].append(p)
            else:
                words.append([p])
        toks: list[Token] = []
        for w in (w for w in words if w):
            text = "".join(p[3]["text"] for p in w)
            if len(text) != len(w):  # a multi-character glyph: keep the word whole
                toks.append(Token(text, w[0][0], w[-1][1], g[0][2], w[0][3]["size"]))
                continue
            for s, e, tok in annex.tokens(text):
                toks.append(Token(tok, w[s][0], w[e - 1][1], g[0][2], w[s][3]["size"]))
        if toks:
            out.append(Line(statistics.median(p[2] for p in g), toks))
    return out


def _split(line: Line) -> None:
    k = next((i for i, t in enumerate(line.tokens) if annex.kind(t.text)), len(line.tokens))
    line.name = line.tokens[:k]
    line.values = line.tokens[k:]
    line.text_after_values = any(annex.kind(t.text) is None for t in line.values)


# ---- rows ---------------------------------------------------------------------

def _rows(lines: list[Line], year: int) -> tuple[list[Row], set[int]]:
    """Rows from the name fragments, and the indices of text lines that are not
    part of a row name (headers and footers, checked later)."""
    rows: list[Row] = []
    other: set[int] = set()
    cur: Row | None = None
    for i, ln in enumerate(lines):
        if not ln.name:
            continue
        frag = " ".join(t.text for t in ln.name)
        if cur is not None and crosswalk.is_prefix(cur.name + " " + frag, year):
            cur.name += " " + frag
            cur.lines.append(i)
        elif crosswalk.is_prefix(frag, year):
            if cur is not None:
                rows.append(cur)
            cur = Row(frag, [i])
        else:
            other.add(i)
    if cur is not None:
        rows.append(cur)
    for r in rows:
        if not crosswalk.is_complete(r.name, year):
            raise ValueError(f"incomplete unit name {r.name!r} on lines "
                             f"{[lines[i].text for i in r.lines]!r}")
        vs = [lines[i].v for i in r.lines]
        r.vc = (min(vs) + max(vs)) / 2
        for i in r.lines:
            lines[i].row = rows.index(r)
    return rows, other


def _cells(lines: list[Line], max_dv: float) -> list[PCell]:
    cells: list[PCell] = []
    pending: list[tuple[int, Token]] = []
    for i, ln in enumerate(lines):
        last: PCell | None = None
        for t in ln.values:
            k = annex.kind(t.text)
            if k == "pct":
                if (last is not None and last.count is not None and not last.blank
                        and last.pct is None and t.u0 - last.count.u1 <= INLINE_GAP * t.size):
                    last.pct, last.pct_line = t, i
                else:
                    pending.append((i, t))
                last = None
                continue
            if k is None:
                last = None
                continue
            last = PCell(t, None, k == "blank", i)
            cells.append(last)
    for i, t in pending:
        best: tuple[float, float, PCell] | None = None
        for c in cells:
            if c.blank or c.pct is not None or c.count is None:
                continue
            dv = t.v - c.count.v
            if not 0 < dv <= max_dv:
                continue
            du = abs(c.count.uc - t.uc)
            if du > 0.6 * max(c.count.u1 - c.count.u0, t.u1 - t.u0):
                continue
            if best is None or (dv, du) < best[:2]:
                best = (dv, du, c)
        if best is not None:
            best[2].pct, best[2].pct_line = t, i
        else:
            cells.append(PCell(None, t, True, i))
    return cells


def read_page(chars: list[dict], width: float, height: float, year: int, ncells: int,
              region: tuple[float, float] | None = None) -> PageRows:
    """The State/UT rows (and the national row, if printed) of one table page."""
    lines = lines_of(chars, width, height, region)
    for ln in lines:
        _split(ln)
    rows, other = _rows(lines, year)
    if not rows:
        raise ValueError("no State/UT row on the page")
    first = min(lines[i].v for i in rows[0].lines)
    last = max(lines[i].v for i in rows[-1].lines)
    centres = [r.vc for r in rows]
    pitch = statistics.median(b - a for a, b in zip(centres, centres[1:])) if len(rows) > 1 \
        else 3 * statistics.median(t.size for ln in lines for t in ln.tokens)
    maxd = MAX_ROW_DIST * pitch
    ignored: list[str] = []
    for i, ln in enumerate(lines):
        inside = first <= ln.v <= last
        if i in other or (ln.row is None and ln.name):
            if inside:
                raise ValueError(f"text line inside the table: {ln.text!r}")
            ignored.append(ln.text)
            ln.values = []  # a title, header or footnote line
            continue
        if ln.text_after_values:
            if inside:
                raise ValueError(f"text after values inside the table: {ln.text!r}")
            ignored.append(ln.text)
            ln.values = []  # a footer such as "153 INDIA TB REPORT 2022 ..."
    cells = _cells(lines, STACK_DV * pitch)
    for c in cells:
        own = lines[c.line].row
        if own is None and c.pct_line is not None:
            own = lines[c.pct_line].row
        if own is not None:
            c.row = own
            continue
        v = c.tok.v if c.pct is None or c.pct_line == c.line else (c.tok.v + c.pct.v) / 2
        d = sorted((abs(v - r.vc), j) for j, r in enumerate(rows))
        if v < first - maxd or v > last + maxd:
            ignored.append(c.cell().raw)
            continue
        if d[0][0] > maxd or (len(d) > 1 and d[0][0] > NEAR_RATIO * d[1][0]):
            raise ValueError(f"cell {c.cell().raw!r} cannot be placed in a row "
                             f"(distances {[(round(x, 1), rows[j].name) for x, j in d[:2]]})")
        c.row = d[0][1]
    for c in cells:
        if c.row is not None:
            rows[c.row].cells.append(c)
    for r in rows:
        r.cells.sort(key=lambda c: c.uc)
        if len(r.cells) > ncells:
            raise ValueError(f"{r.name}: {len(r.cells)} cells, table has {ncells}: "
                             f"{[c.cell().raw for c in r.cells]}")
    full = [r for r in rows if len(r.cells) == ncells]
    if not full:
        raise ValueError(f"no row on the page prints all {ncells} cells")
    centre = [statistics.median(r.cells[k].uc for r in full) for k in range(ncells)]

    def nearest(u: float) -> int:
        return min(range(ncells), key=lambda k: abs(u - centre[k]))

    out: dict[str, list[annex.Cell | None]] = {}
    national: list[annex.Cell | None] | None = None
    raw_names: dict[str, str] = {}
    for r in rows:
        placed: list[annex.Cell | None] = [None] * ncells
        if len(r.cells) == ncells:
            for k, c in enumerate(r.cells):
                if nearest(c.uc) != k:
                    raise ValueError(f"{r.name}: cell {c.cell().raw!r} (column {k + 1}) lies "
                                     f"nearer column {nearest(c.uc) + 1}")
                placed[k] = c.cell()
        else:
            for c in r.cells:
                k = nearest(c.uc)
                if placed[k] is not None:
                    raise ValueError(f"{r.name}: two cells in column {k + 1}: "
                                     f"{[x.cell().raw for x in r.cells]}")
                placed[k] = c.cell()
        if crosswalk.is_national(r.name):
            if national is not None:
                raise ValueError("two national rows on the page")
            national = placed
            raw_names[crosswalk.NATIONAL] = r.name
            continue
        canon = crosswalk.printed_unit(r.name, year)
        if canon in out:
            raise ValueError(f"two rows for {canon} on the page")
        out[canon] = placed
        raw_names[canon] = r.name
    return PageRows(out, national, raw_names, ignored)
