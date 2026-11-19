"""Packed cell values: repPackSemIds, repPackValueInfo, repPackDescr (fmt=1..4).

Line breaks are kept as in the C# code (`\\r\\n`, `%BRPOST%`); the AsciiDoc writer resolves them.
"""

from excel_to_aasx.domain.document.tables.model import Concept, Element, LangText, Ref

BR = "\r\n%BRPOST%"
EXAMPLE_VALUE = "SMT/ExampleValue"
UNIT_OF_MEASURE = "SME/UnitOfMeasure"


def has_content(text: str | None) -> bool:
    return bool(text and text.strip())


def default_text(texts: tuple[LangText, ...]) -> str:
    """GetDefaultString: English, else the first entry."""
    for language, text in texts:
        if language.strip().lower() == "en":
            return text
    return texts[0][1] if texts else ""


def pack_semantic_ids(
    semantic_id: Ref | None, supplemental: tuple[Ref, ...], is_case_of: tuple[Ref, ...]
) -> dict[int, str]:
    labels = {
        1: ("", "%BRPOST%", "", "%BRPOST%"),
        2: ("SSI: ", "%BRPOST%SSI: ", "ICO: ", "%BRPOST%ICO: "),
        3: ("supplementalSemanticId(s):\r\n", "%BRPOST% ", "isCaseOf:\r\n", "%BRPOST% "),
    }
    result = {}
    for fmt in (1, 2, 3, 4):
        sup_label, sup_sep, ico_label, ico_sep = labels[min(fmt, 3)]
        value = semantic_id.text(2, ", ") + " " if semantic_id and semantic_id.keys else ""
        for refs, label, separator in (
            (supplemental, sup_label, sup_sep),
            (is_case_of, ico_label, ico_sep),
        ):
            if refs:
                if has_content(value):
                    value += BR
                value += label + separator.join(r.text(2) for r in refs) + " "
        if fmt == 4 and has_content(value):
            value += BR
        result[fmt] = value
    return result


def pack_value(element: Element, concept: Concept | None) -> dict[int, str]:
    value_type = f"[{element.value_type}]" if element.kind == "Property" else ""
    value = _shorten(element.value_text, 80)
    example = _qualifier(element, EXAMPLE_VALUE)
    if has_content(example):
        value = example
    unit = (
        f"({_qualifier(element, UNIT_OF_MEASURE)})"
        if has_content(_qualifier(element, UNIT_OF_MEASURE))
        else ""
    )
    if concept is not None and concept.unit:
        unit = f"({concept.unit})"
    value_id = element.value_id.text(1) if element.value_id and element.value_id.keys else ""
    cells = {
        1: (value_type, value),
        2: (value_type, value, unit),
        3: (value_type, value, value_id),
        4: (value_type, value, unit, value_id),
    }
    return {fmt: _join(parts) for fmt, parts in cells.items()}


def pack_description(element: Element, concept: Concept | None) -> dict[int, str]:
    definition = default_text(concept.definitions) if concept and concept.definitions else ""
    description = default_text(element.description)
    result = {1: _join((definition, description))}
    for fmt in (2, 3, 4):
        result[fmt] = _join((definition, description, _value_list(concept, fmt)))
    return result


def _value_list(concept: Concept | None, fmt: int) -> str:
    if concept is None or concept.value_list is None:
        return ""
    if fmt == 2:
        return f"Value list items: {len(concept.value_list)}"
    items = [
        f"{value.strip()}={ref.text(2)}" if fmt == 4 and ref and ref.keys else value.strip()
        for value, ref in concept.value_list
    ]
    return "Value list items:\r\n" + ", ".join(items)


def _qualifier(element: Element, kind: str) -> str:
    return next((value for q_type, value in element.qualifiers if q_type == kind), "")


def _shorten(text: str, limit: int) -> str:
    return text[:limit] + "…" if len(text) > limit else text


def _join(parts: tuple[str, ...]) -> str:
    return BR.join(part for part in parts if has_content(part))
