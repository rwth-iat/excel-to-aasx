"""Write one container's table in AsciiDoc (ExportTableProcessor.ExportAsciiDoc).

Works with the C# line ends (`\\r\\n`) so the post-processing splits the same way, and
converts to `\\n` at the end.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from excel_to_aasx.domain.document.tables.cells import Cell, CellFiller
from excel_to_aasx.domain.document.tables.model import Element
from excel_to_aasx.domain.document.tables.placeholders import placeholders_for
from excel_to_aasx.domain.document.tables.preset import TablePreset

NL = "\r\n"


@dataclass(frozen=True)
class TableRequest:
    container: Element
    parent: Element | None
    element_id: str
    title: str
    column_widths: tuple[float, ...] | None = None


@dataclass
class _Colors:
    table_bg: str
    current: str | None = None
    started: bool = False


def write_table(preset: TablePreset, request: TableRequest) -> list[str]:
    """The table file as lines (NoHeadings, depth 1: one table of direct children)."""
    out = [""]
    items = request.container.children
    if not items:
        return [line.replace("\r", "") for line in out]
    fail_text = preset.fail_text if preset.replace_failed_matches else None
    top = CellFiller(
        placeholders_for(items[0], 1, request.container, request.parent),
        fail_text,
        request.column_widths,
    )
    out.append("")
    widths = [top.fill(*preset.top_cell(0, col), col).width for col in range(preset.cols)]
    cols = ",".join(f"{w:.0f}%" if w is not None else "1" for w in widths)
    element_id = f' id="{request.element_id}",' if request.element_id else ""
    title = f' title="{request.title}",' if request.title else ""
    out.append(f'[width="100%",{element_id}{title} cols="{cols}"]')
    out.append("|===")
    first = top.fill(*preset.top_cell(0, 0), 0)
    colors = _Colors(first.table_bg) if first.table_bg else None
    for row in range(preset.rows_top):
        out.append(_row(preset, top, colors, row, preset.top_cell))
    out.extend(["", ""])
    for item in items:
        filler = CellFiller(
            placeholders_for(item, 1, request.container, request.parent),
            fail_text,
            request.column_widths,
        )
        lines = []
        for row in range(preset.rows_body):
            lines.extend([_row(preset, filler, colors, row, preset.body_cell), "", ""])
        if filler.replacements > 0:
            out.extend(lines)
    out.append("|===")
    out.extend([""] * max(0, preset.rows_gap))
    text = NL.join(out)
    return text.replace("\r\n", "\n").replace("\r", "").split("\n")


def _row(
    preset: TablePreset,
    filler: CellFiller,
    colors: _Colors | None,
    row: int,
    cell_of: Callable[[int, int], tuple[str, str]],
) -> str:
    line, skip = "", 0
    for col in range(preset.cols):
        if skip > 0:
            skip -= 1
            continue
        text, with_headers = cell_of(row, col)
        cell = filler.fill(text, with_headers, col)
        text, skip = _column_text(cell, colors)
        line += _post_process(text)
    return line  # ends with NL, so each row is followed by an empty line


def _column_text(cell: Cell, colors: _Colors | None) -> tuple[str, int]:
    """ExportAsciiDocEvalColumnText. Returns the text and how many columns the span covers."""
    start, skip = "", 0
    if cell.col_span > 1:
        start, skip = f"{cell.col_span}+", cell.col_span - 1
    if cell.font is not None:
        start += "s" if "bold" in cell.font else ""
        start += "e" if "italic" in cell.font else ""
        start += "h" if "header" in cell.font else ""
    start += "|" + _background(cell, colors)
    body = cell.text.replace("|", "\\|")
    if cell.fg is not None and re.search(r"[a-zA-Z.]+", cell.fg):
        body = f" [{cell.fg}]#" + body.replace("#", "\\#").strip() + "#"
    return start + body + NL, skip


def _background(cell: Cell, colors: _Colors | None) -> str:
    if colors is None:
        return ""
    wanted = cell.bg if cell.bg and cell.bg.strip() else None
    if not colors.started:
        colors.started = True
        colors.current = wanted or colors.table_bg
        return "{set:cellbgcolor:" + colors.current + "}"
    if wanted and wanted != colors.current:
        colors.current = wanted
        return "{set:cellbgcolor:" + wanted + "}"
    if not wanted and colors.current != colors.table_bg:
        colors.current = colors.table_bg
        return "{set:cellbgcolor:" + colors.table_bg + "}"
    return ""


def _post_process(text: str) -> str:
    """ExportAsciiDocPostProcessAsciiDoc: explicit line breaks become ` +` hard breaks."""
    parts = [p for p in re.split(r"\+\r\n|\+\r|\r\n\r\n", text) if p and p.strip()]
    result = (" +" + NL).join(parts).rstrip("\r\n") + NL
    return result.replace("%BRPOST%", " +" + NL)
