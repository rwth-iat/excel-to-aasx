"""Turn blocks into a submodel and its concept descriptions (spec sections 4-7)."""

import hashlib
from collections.abc import Iterator, Sequence

from excel_to_aasx.domain.ids import remove_version
from excel_to_aasx.domain.importing.blocks import Block, BodyRow, Top
from excel_to_aasx.domain.importing.cells import (
    is_valid_id_short,
    parse_cardinality,
    parse_element_kind,
    parse_lang_strings,
    parse_value_type,
)
from excel_to_aasx.domain.importing.hierarchy import Hierarchy
from excel_to_aasx.domain.importing.model import Concept, Element, LangText, SubmodelDraft
from excel_to_aasx.domain.importing.result import ImportResult, Issue

CD_ID_TEMPLATE = "www.example.com/ids/cd/DDDD_DDDD_DDDD_DDDD"
# Need data the sheet does not have (observed reference, direction, state).
_UNSUPPORTED_KINDS = frozenset({"BasicEventElement"})
_VALUE_TYPED_KINDS = frozenset({"Property", "Range"})


def build_submodel(blocks: Sequence[Block], submodel: SubmodelDraft) -> ImportResult:
    builder = _Builder(submodel)
    for block in blocks:
        builder.add_block(block)
    builder.check_id_shorts()
    return builder.result


def generated_id(template: str, seed: str) -> str:
    """Fill each `D` of `template` with digits derived from `seed` (stable across runs)."""
    digits = iter(str(int(hashlib.sha256(seed.encode()).hexdigest(), 16)))
    return "".join(next(digits) if char == "D" else char for char in template)


class _Builder:
    def __init__(self, submodel: SubmodelDraft) -> None:
        self.result = ImportResult(submodel)
        self._concepts: dict[str, Concept] = {}
        self._hierarchy = Hierarchy()

    @property
    def _submodel(self) -> SubmodelDraft:
        return self.result.submodel

    def add_block(self, block: Block) -> None:
        container = self._container_for(block.top)
        if container is None:
            self._issue(
                "error",
                block.top.location,
                f"block skipped: Class '{block.top.element_name}' is not Submodel, SMC or SML",
            )
            return
        parent_id_short, children = container
        for row in block.body:
            self._add_row(row, parent_id_short, children)

    def _container_for(self, top: Top) -> tuple[str, list[Element]] | None:
        kind = parse_element_kind(top.element_name)
        if kind == "Submodel":
            self._take_over(top)
            return self._submodel.id_short, self._submodel.elements
        if kind == "SubmodelElementCollection":
            found = self._hierarchy.find(
                self._submodel.id_short, self._submodel.elements, top.id_short,
                top.semantic_id.strip(), top.parent_name,
            )  # fmt: skip
            if found is not None:
                return found.id_short, found.children
        if kind not in ("SubmodelElementCollection", "SubmodelElementList"):
            return None
        element = Element(
            kind,
            top.id_short,
            top.semantic_id.strip(),
            description=parse_lang_strings(top.explanation),
        )
        self._submodel.elements.append(element)
        return element.id_short, element.children

    def _take_over(self, top: Top) -> None:
        """AasConvertHelper.TakeOverSmeToSm."""
        self._submodel.description = parse_lang_strings(top.explanation)
        if top.id_short:
            self._submodel.id_short = top.id_short
        if top.semantic_id.strip():
            self._submodel.semantic_id = top.semantic_id.strip()

    def _add_row(self, row: BodyRow, parent_id_short: str, siblings: list[Element]) -> None:
        kind = parse_element_kind(row.element_name)
        if kind is None or kind == "Submodel" or kind in _UNSUPPORTED_KINDS:
            self._issue(
                "error",
                row.location,
                f"row skipped: unsupported SME.elementName '{row.element_name}'",
            )
            return
        if any(s.id_short == row.sme_id_short for s in siblings):
            self._issue(
                "error",
                row.location,
                f"row skipped: idShort '{row.sme_id_short}' already exists in '{parent_id_short}'",
            )
            return
        semantic_id = row.sme_semantic_id.strip() or generated_id(
            CD_ID_TEMPLATE, f"{self._submodel.id}/{parent_id_short}/{row.sme_id_short}"
        )
        self._add_concept(row, semantic_id)
        siblings.append(
            Element(
                kind, row.sme_id_short, semantic_id,
                display_names=_texts(("en", row.display_name_en), ("de", row.display_name_de)),
                cardinality=parse_cardinality(row.multiplicity),
                value_type=self._value_type(row) if kind in _VALUE_TYPED_KINDS else "",
            )
        )  # fmt: skip

    def _value_type(self, row: BodyRow) -> str:
        value_type, meant = parse_value_type(row.value_type)
        if meant:
            self._issue(
                "warning",
                row.location,
                f"value type '{row.value_type}' is not an XSD type name; "
                f"imported as xs:string (did you mean {meant}?)",
            )
        return value_type or "xs:string"

    def _add_concept(self, row: BodyRow, concept_id: str) -> None:
        key = remove_version(concept_id)
        if key in self._concepts:
            return
        concept = Concept(
            concept_id,
            row.cd_id_short or row.sme_id_short,
            preferred_names=tuple(
                _texts(("en", row.preferred_name_en), ("de", row.preferred_name_de))
            ),
            definitions=tuple(_texts(("en", row.definition_en), ("de", row.definition_de))),
            unit=row.unit,
        )
        self._concepts[key] = concept
        self.result.concepts.append(concept)

    def check_id_shorts(self) -> None:
        for path, element in _walk(self._submodel.elements, ""):
            if not is_valid_id_short(element.id_short):
                self._issue("warning", path, f"idShort '{element.id_short}' is not a valid idShort")
        for concept in self.result.concepts:
            if not is_valid_id_short(concept.id_short):
                self._issue(
                    "warning", concept.id, f"CD idShort '{concept.id_short}' is not a valid idShort"
                )

    def _issue(self, severity: str, location: str, message: str) -> None:
        self.result.issues.append(Issue(severity, location, message))


def _texts(*pairs: LangText) -> list[LangText]:
    return [(language, text) for language, text in pairs if text.strip()]


def _walk(elements: list[Element], prefix: str) -> Iterator[tuple[str, Element]]:
    for element in elements:
        path = f"{prefix}/{element.id_short}" if prefix else element.id_short
        yield path, element
        yield from _walk(element.children, path)
