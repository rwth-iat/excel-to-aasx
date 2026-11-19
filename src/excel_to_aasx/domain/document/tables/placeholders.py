"""The `%placeholder%` values for one table row (ItemProcessor.Start and its rep* helpers)."""

import re
from dataclasses import dataclass, field

from excel_to_aasx.domain.document.tables.model import Concept, Element, LangText
from excel_to_aasx.domain.document.tables.packs import (
    default_text,
    pack_description,
    pack_semantic_ids,
    pack_value,
)

CARDINALITY = "SMT/Cardinality"
_CARDINALITY_TEXT = {"One": "1", "ZeroToOne": "0..1", "ZeroToMany": "0..*", "OneToMany": "1..*"}
ABBREVIATIONS = {
    "Submodel": "SM", "ConceptDescription": "CD", "Property": "Prop",
    "MultiLanguageProperty": "MLP", "Range": "Range", "Blob": "Blob", "File": "File",
    "ReferenceElement": "Ref", "RelationshipElement": "Rel",
    "AnnotatedRelationshipElement": "RelA", "Capability": "Cap",
    "SubmodelElementCollection": "SMC", "SubmodelElementList": "SML", "Operation": "Opr",
    "Entity": "Ent", "BasicEventElement": "Evt",
}  # fmt: skip


@dataclass
class Placeholders:
    """Lower-case tag -> text. The first value set for a tag wins, as in `rep()`."""

    values: dict[str, str] = field(default_factory=dict)
    # (trigger, pattern, replacement with %GROUP1%)
    advanced: list[tuple[str, str, str]] = field(default_factory=list)

    def set(self, tag: str, value: str) -> None:
        self.values.setdefault(tag.strip().lower(), value)


def placeholders_for(
    item: Element, depth: int, parent: Element, grandparent: Element | None
) -> Placeholders:
    ph = Placeholders()
    for tag, value in (("nl", "\r\n"), ("br", "\r"), ("tab", "\t"), ("brpost", "%BRPOST%")):
        ph.set(tag, value)
    ph.set("depth", str(depth))
    ph.set("indent", "~" * max(0, depth))
    _referable(ph, "Parent.", parent, grandparent)
    _multiplicity(ph, "Parent.", parent)
    _semantics(ph, "Parent.", parent, parent.concept)
    definition = parent.concept.definitions if parent.concept else ()
    ph.set("Parent.definition@en", default_text(definition) if definition else "")
    _referable(ph, "SME.", item, parent)
    _multiplicity(ph, "SME.", item)
    _semantics(ph, "SME.", item, item.concept)
    for fmt, text in pack_description(item, item.concept).items():
        ph.set(f"SME.packDescription[fmt={fmt}]", text)
    for fmt, text in pack_value(item, item.concept).items():
        ph.set(f"SME.packValue[fmt={fmt}]", text)
    _values(ph, item)
    if item.concept is not None:
        _concept(ph, item.concept)
    return ph


def _referable(ph: Placeholders, head: str, rf: Element, parent: Element | None) -> None:
    ph.set(head + "idShort", _escape(rf.id_short))
    _lang_list(ph, head + "description", rf.description)
    ph.set(head + "elementName", rf.kind)
    ph.set(head + "elementAbbreviation", ABBREVIATIONS.get(rf.kind, ""))
    if rf.kind != "Submodel":
        ph.set(head + "elementShort", ABBREVIATIONS.get(rf.kind, ""))
    if parent is None:
        ph.set(head + "parent", "-")
    else:
        ph.set(head + "parent", _escape(parent.id_short or "-"))
        _lang_list(ph, head + "parent.description", parent.description)
    ph.set(head + "details", ", ".join(rf.details) or "-")


def _multiplicity(ph: Placeholders, head: str, rf: Element) -> None:
    value = next((v for t, v in rf.qualifiers if t == CARDINALITY), None)
    text = _CARDINALITY_TEXT.get(value, "1") if value is not None else ""
    ph.set(head + "multiplicity", text)


def _semantics(ph: Placeholders, head: str, rf: Element, concept: Concept | None) -> None:
    if rf.semantic_id is not None:
        ph.set(head + "semanticId", rf.semantic_id.text(1))
        for index, (kind, value) in enumerate(rf.semantic_id.keys):
            ph.set(f"{head}semanticId[{index}]", f"[{kind}, {value}]")
            ph.set(f"{head}semanticId[{index}].type", kind)
            ph.set(f"{head}semanticId[{index}].value", value)
    supplemental = ", ".join(r.text(2) for r in rf.supplemental_ids)
    ph.set(head + "supplSemIds", supplemental)
    ph.set(
        head + "supplSemIds[br]",
        "\r\n%BRPOST%%BRPOST%".join(r.text(2) for r in rf.supplemental_ids),
    )
    if rf.supplemental_ids:
        ph.advanced.append(
            (
                f"{head}supplSemIds".lower(),
                rf"{re.escape(head)}supplSemIds\[label=([^]]*)\]",
                f"%GROUP1%: {supplemental}",
            )
        )
        ph.advanced.append(
            (
                f"{head}supplSemIds".lower(),
                rf"{re.escape(head)}supplSemIds\[br-label=([^]]*)\]",
                f"%GROUP1%: {supplemental}%BRPOST%%BRPOST%",
            )
        )
    else:
        for label in ("label", "br-label"):
            ph.advanced.append(
                (
                    f"{head}supplSemIds".lower(),
                    rf"{re.escape(head)}supplSemIds\[{label}=([^]]*)\]",
                    "",
                )
            )
    is_case_of = concept.is_case_of if concept else ()
    for fmt, text in pack_semantic_ids(rf.semantic_id, rf.supplemental_ids, is_case_of).items():
        ph.set(f"{head}packSemIds[fmt={fmt}]", text)


def _values(ph: Placeholders, item: Element) -> None:
    if item.kind == "Property":
        ph.set("Property.value", item.value_text)
        ph.set("Property.valueType", item.value_type)
        if item.value_id is not None:
            ph.set("Property.valueId", item.value_id.text(1))
    if item.kind in ("SubmodelElementCollection", "SubmodelElementList"):
        ph.set(f"{item.kind}.value", f"{len(item.children)} elements")
        ph.set("SME.value", f"{len(item.children)} elements")
    ph.set("SME.value", item.value_text)


def _concept(ph: Placeholders, concept: Concept) -> None:
    ph.set("CD.idShort", _escape(concept.id_short))
    ph.set("CD.elementName", "ConceptDescription")
    ph.set("CD.parent", "-")
    ph.set("CD.id", concept.id)
    for language, text in concept.preferred_names:
        ph.set(f"CD.preferredName@{language}", text)
    ph.set("CD.unit", concept.unit)
    _lang_list(ph, "CD.definition", concept.definitions, whole=False)
    names = concept.preferred_names
    ph.set("CD.anyName", default_text(names) if names else concept.id_short)


def _lang_list(
    ph: Placeholders, head: str, texts: tuple[LangText, ...], whole: bool = True
) -> None:
    """repListOfLangStr: per language, several entries of one language joined by blank lines."""
    if not texts:
        return
    if whole:
        ph.set(head, ", ".join(f"{text}@{language}" for language, text in texts))
    by_language: dict[str, list[str]] = {}
    for language, text in texts:
        by_language.setdefault(language, []).append(text)
    for language, entries in by_language.items():
        ph.set(f"{head}@{language}", "\r\n\r\n".join(entries))


def _escape(text: str) -> str:
    """escapeLiteralsToFormat: `__00__` would start AsciiDoc emphasis."""
    for literal in ("__0000__", "__000__", "__00__"):
        text = text.replace(literal, "\\" + literal)
    return text
