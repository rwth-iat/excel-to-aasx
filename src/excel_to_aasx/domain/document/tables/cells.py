"""Fill one template cell and read its formatting (ItemProcessor.ProcessCellRecord)."""

import re
from dataclasses import dataclass

from excel_to_aasx.domain.document.tables.placeholders import Placeholders

_REPLACEMENT = re.compile(r"%([a-zA-Z0-9.@\[\]=-]+)%", re.IGNORECASE)
_STOP = re.compile(r"^(.*?)%stop%(.*)$", re.IGNORECASE)
_COMMAND = re.compile(r"(%([A-Za-z0-9_-]+)=(.*?)%)", re.IGNORECASE)
_STYLE_COMMANDS = {
    "fg": "fg", "bg": "bg", "table-bg": "table_bg", "halign": "h_align",
    "valign": "v_align", "font": "font", "frame": "frame", "md": "md",
}  # fmt: skip


@dataclass
class Cell:
    text: str
    col: int
    fg: str | None = None
    bg: str | None = None
    table_bg: str | None = None
    h_align: str | None = None
    v_align: str | None = None
    font: str | None = None
    frame: str | None = None
    md: str | None = None
    width: float | None = None
    col_span: int = 1


@dataclass
class CellFiller:
    placeholders: Placeholders
    fail_text: str | None  # None: leave unknown placeholders as they are
    column_widths: tuple[float, ...] | None = None
    replacements: int = 0

    def fill(self, text: str, with_headers: str, col: int) -> Cell:
        cell = Cell(self._replace(text), col)
        for whole, name, argument in reversed(_COMMAND.findall(with_headers)):
            self._command(cell, name.strip().lower(), argument)
            position = cell.text.rfind(whole)
            if position >= 0:
                cell.text = cell.text[:position] + cell.text[position + len(whole) :]
        cell.text = cell.text.replace("\r\n", " +\r\n").replace("\n\r", " +\r\n")
        return cell

    def _replace(self, text: str) -> str:
        for match in reversed(list(_REPLACEMENT.finditer(text))):
            tag = match.group(1).strip()
            value = self._advanced(tag)
            if value is None:
                value = self.placeholders.values.get(tag.lower())
            if value is not None:
                self.replacements += 1
            elif tag.lower() == "stop" or self.fail_text is None:
                continue
            else:
                value = self.fail_text
            text = text[: match.start()] + value + text[match.end() :]
        while stop := _STOP.match(text):
            left, right = stop.group(1).strip(), stop.group(2).strip()
            text = left if left else right
        return text

    def _advanced(self, tag: str) -> str | None:
        result = None
        for trigger, pattern, replacement in self.placeholders.advanced:
            if trigger in tag.lower() and (found := re.search(pattern, tag, re.IGNORECASE)):
                result = replacement
                for index, group in enumerate(found.groups(), start=1):
                    result = result.replace(f"%GROUP{index}%", group or "")
        return result

    def _command(self, cell: Cell, name: str, argument: str) -> None:
        value = argument.strip().lower()
        if name in _STYLE_COMMANDS:
            setattr(cell, _STYLE_COMMANDS[name], value)
        elif name == "width":
            preferred = self.column_widths
            if preferred and cell.col < len(preferred) and 0 <= preferred[cell.col] <= 100:
                cell.width = preferred[cell.col]
            else:
                cell.width = _number(value)
        elif name == "colspan" and value.isdigit() and int(value) >= 2:
            cell.col_span = int(value)
        elif name == "trim" and value == "all":
            cell.text = cell.text.strip()


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None
