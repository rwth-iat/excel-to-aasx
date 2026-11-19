"""The "act in hierarchy" lookup of ImportPopulateByTable.CreateTopReferable (spec 4.2)."""

import re
from collections.abc import Iterator

from excel_to_aasx.domain.importing.model import Element


class Hierarchy:
    """Finds the existing collection a block continues. Remembers names it resolved."""

    def __init__(self) -> None:
        # idShort of a found collection -> block idShorts that resolved to it
        self._aliases: dict[str, list[str]] = {}

    def find(
        self,
        root_id_short: str,
        roots: list[Element],
        top_id_short: str,
        top_semantic_id: str,
        parent_name: str,
    ) -> Element | None:
        if not parent_name or not top_id_short:
            return None
        parts = {p.strip().lower() for p in re.split(r"[,;|]", top_id_short) if p.strip()}
        wanted_parent = parent_name.lower()
        for parent_id_short, candidate in _collections(root_id_short, roots):
            if not candidate.id_short or not self._parent_matches(parent_id_short, wanted_parent):
                continue
            same_name = candidate.id_short.strip().lower() in parts
            same_semantics = bool(top_semantic_id) and candidate.semantic_id == top_semantic_id
            if same_name or same_semantics:
                self._aliases.setdefault(candidate.id_short, []).append(top_id_short)
                return candidate
        return None

    def _parent_matches(self, parent_id_short: str, wanted_parent: str) -> bool:
        if parent_id_short.strip().lower() in wanted_parent:
            return True
        return any(
            alias.strip().lower() in wanted_parent
            for alias in self._aliases.get(parent_id_short, [])
        )


def _collections(parent_id_short: str, elements: list[Element]) -> Iterator[tuple[str, Element]]:
    """Pre-order walk over collections only; FindDeep<SubmodelElementCollection> skips lists."""
    for element in elements:
        if element.kind == "SubmodelElementCollection":
            yield parent_id_short, element
            yield from _collections(element.id_short, element.children)
