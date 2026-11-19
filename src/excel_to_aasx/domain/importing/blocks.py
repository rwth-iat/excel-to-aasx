"""Find import blocks in a sheet (spec section 2). Rows are lists of cell texts."""

from collections.abc import Sequence
from dataclasses import dataclass

COLUMNS = 13
TOP_ROWS = 6
TOP_LABELS = ("idShort:", "Class:", "semanticId:", "Parent:", "Explanation:")
MAX_EMPTY_ROWS = 100


@dataclass(frozen=True)
class Top:
    location: str
    id_short: str
    element_name: str
    semantic_id: str
    parent_name: str
    explanation: str


@dataclass(frozen=True)
class BodyRow:
    location: str
    sme_id_short: str
    sme_semantic_id: str
    display_name_en: str
    display_name_de: str
    cd_id_short: str
    preferred_name_en: str
    preferred_name_de: str
    definition_en: str
    definition_de: str
    unit: str
    element_name: str
    value_type: str
    multiplicity: str


@dataclass(frozen=True)
class Block:
    top: Top
    body: tuple[BodyRow, ...]


def find_blocks(sheet: str, rows: Sequence[Sequence[str]]) -> list[Block]:
    grid = [_padded(row) for row in rows]
    blocks: list[Block] = []
    index, empty_run = 0, 0
    while index + TOP_ROWS < len(grid):
        if not any(grid[index]):
            empty_run += 1
            if empty_run >= MAX_EMPTY_ROWS:
                break
            index += 1
            continue
        empty_run = 0
        if not _is_top(grid, index):
            index += 1
            continue
        body_start = index + TOP_ROWS
        body_end = body_start
        while body_end < len(grid) and any(grid[body_end]):
            body_end += 1
        top = Top(f"{sheet}!{index + 1}", *(grid[index + k][1] for k in range(5)))
        body = tuple(BodyRow(f"{sheet}!{r + 1}", *grid[r]) for r in range(body_start, body_end))
        blocks.append(Block(top, body))
        index = body_end
    return blocks


def _padded(row: Sequence[str]) -> list[str]:
    cells = list(row[:COLUMNS])
    return cells + [""] * (COLUMNS - len(cells))


def _is_top(grid: list[list[str]], index: int) -> bool:
    return all(grid[index + k][0] == label for k, label in enumerate(TOP_LABELS))
