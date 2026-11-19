"""A table preset (ImportExportTableRecord) and its cells (GetTopCell / GetBodyCell)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from excel_to_aasx.domain.document.tables.builtin import SMT_ASCIIDOC


@dataclass(frozen=True)
class TablePreset:
    rows_top: int
    rows_body: int
    rows_gap: int
    cols: int
    replace_failed_matches: bool
    fail_text: str
    top: tuple[str, ...]
    body: tuple[str, ...]

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "TablePreset":
        """From the JSON of a preset or a `tablerecord` blob. Raises `ValueError` if unusable."""
        try:
            preset = cls(
                rows_top=int(record["RowsTop"]),
                rows_body=int(record["RowsBody"]),
                rows_gap=int(record.get("RowsGap", 0)),
                cols=int(record["Cols"]),
                replace_failed_matches=bool(record.get("ReplaceFailedMatches", False)),
                fail_text=str(record.get("FailText", "")),
                top=tuple(str(x) for x in record["Top"]),
                body=tuple(str(x) for x in record["Body"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"table preset is incomplete: {error}") from error
        if preset.cols < 1 or preset.rows_top < 0 or preset.rows_body < 1:
            raise ValueError("table preset needs at least one column and one body row")
        return preset

    def top_cell(self, row: int, col: int) -> tuple[str, str]:
        """(text, text with table, row and column headers), as GetTopCell."""
        return _cell(self.top, self.cols, row, col)

    def body_cell(self, row: int, col: int) -> tuple[str, str]:
        return _cell(self.body, self.cols, row, col)


def _cell(cells: tuple[str, ...], cols: int, row: int, col: int) -> tuple[str, str]:
    index = (1 + row) * (1 + cols) + 1 + col
    if index >= len(cells):
        return "", ""
    text = cells[index]
    with_headers = f"{cells[0]} {cells[(1 + row) * (1 + cols)]} {cells[1 + col]} {text}"
    return text, with_headers


SMT_ASCIIDOC_PRESET = TablePreset.from_record(SMT_ASCIIDOC)
