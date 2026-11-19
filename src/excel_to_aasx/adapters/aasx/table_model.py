"""Reduce submodels and their concept descriptions to the table generator's model."""

import aas_core3_1.types as aas

from excel_to_aasx.domain.document.tables.model import Concept, Element, Ref
from excel_to_aasx.domain.ids import remove_version


def table_models(environment: aas.Environment) -> dict[str, Element]:
    concepts: dict[str, Concept] = {}
    for cd in environment.concept_descriptions or []:
        concepts.setdefault(remove_version(cd.id), _concept(cd))
    return {
        submodel.id: Element(
            kind="Submodel",
            id_short=submodel.id_short or "",
            description=_texts(submodel.description),
            semantic_id=_ref(submodel.semantic_id),
            supplemental_ids=tuple(
                r for r in map(_ref, submodel.supplemental_semantic_ids or []) if r
            ),
            qualifiers=_qualifiers(submodel.qualifiers),
            concept=_lookup(concepts, submodel.semantic_id),
            children=tuple(_element(e, concepts) for e in submodel.submodel_elements or []),
        )
        for submodel in environment.submodels or []
    }


def _element(element: aas.SubmodelElement, concepts: dict[str, Concept]) -> Element:
    children: list[aas.SubmodelElement] = []
    if isinstance(element, aas.SubmodelElementCollection | aas.SubmodelElementList):
        children = list(element.value or [])
    value_id = (
        element.value_id if isinstance(element, aas.Property | aas.MultiLanguageProperty) else None
    )
    return Element(
        kind=type(element).__name__,
        id_short=element.id_short or "",
        description=_texts(element.description),
        semantic_id=_ref(element.semantic_id),
        supplemental_ids=tuple(r for r in map(_ref, element.supplemental_semantic_ids or []) if r),
        qualifiers=_qualifiers(element.qualifiers),
        value_text=_value_text(element),
        value_type=element.value_type.value if isinstance(element, aas.Property) else "",
        value_id=_ref(value_id),
        details=_details(element),
        concept=_lookup(concepts, element.semantic_id),
        children=tuple(_element(child, concepts) for child in children),
    )


def _value_text(element: aas.SubmodelElement) -> str:
    """ISubmodelElement.ValueAsText."""
    if isinstance(element, aas.Property | aas.File):
        return element.value or ""
    if isinstance(element, aas.MultiLanguageProperty):
        texts = _texts(element.value)
        return next((t for lang, t in texts if lang.lower() == "en"), texts[0][1] if texts else "")
    if isinstance(element, aas.Range):
        return f"{element.min or ''} .. {element.max or ''}"
    if isinstance(element, aas.Blob):
        return (element.value or b"").decode("utf-8", errors="replace")
    return ""


def _details(element: aas.SubmodelElement) -> tuple[str, ...]:
    if not isinstance(element, aas.SubmodelElementList):
        return ()
    details = [f"orderRelevant={'Yes' if element.order_relevant else 'No'}"]
    if (list_semantics := _ref(element.semantic_id_list_element)) is not None:
        details.append(f"semanticIdListElement={list_semantics.text(1)}")
    details.append(f"typeValueListElement={element.type_value_list_element.value}")
    if element.value_type_list_element is not None:
        details.append(f"valueTypeListElement={element.value_type_list_element.value}")
    return tuple(details)


def _concept(cd: aas.ConceptDescription) -> Concept:
    iec = next(
        (
            spec.data_specification_content
            for spec in cd.embedded_data_specifications or []
            if isinstance(spec.data_specification_content, aas.DataSpecificationIEC61360)
        ),
        None,
    )
    is_case_of = tuple(r for r in map(_ref, cd.is_case_of or []) if r)
    if iec is None:
        return Concept(id=cd.id, id_short=cd.id_short or "", is_case_of=is_case_of)
    value_list = None
    if iec.value_list is not None:
        value_list = tuple(
            (p.value, _ref(p.value_id)) for p in iec.value_list.value_reference_pairs
        )
    return Concept(
        id=cd.id,
        id_short=cd.id_short or "",
        preferred_names=_texts(iec.preferred_name),
        definitions=_texts(iec.definition),
        unit=iec.unit or "",
        value_list=value_list,
        is_case_of=is_case_of,
    )


def _lookup(concepts: dict[str, Concept], reference: aas.Reference | None) -> Concept | None:
    """FindConceptDescriptionByReference; Package Explorer's options set MatchCdNoVersion."""
    if reference is None or len(reference.keys) != 1:
        return None
    return concepts.get(remove_version(reference.keys[0].value))


def _ref(reference: aas.Reference | None) -> Ref | None:
    if reference is None:
        return None
    return Ref(tuple((key.type.value, key.value) for key in reference.keys))


def _texts(texts) -> tuple[tuple[str, str], ...]:
    return tuple((t.language, t.text) for t in texts or [])


def _qualifiers(qualifiers: list[aas.Qualifier] | None) -> tuple[tuple[str, str], ...]:
    return tuple((q.type, q.value or "") for q in qualifiers or [])
