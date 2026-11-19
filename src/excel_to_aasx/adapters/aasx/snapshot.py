"""Reduce an aas-core3.1 environment to the facts the comparison needs."""

from collections.abc import Iterable, Iterator

import aas_core3_1.types as aas

from excel_to_aasx.domain.snapshot import ConceptFacts, ElementFacts, PackageSnapshot

CARDINALITY_QUALIFIER = "SMT/Cardinality"


def snapshot_of(environment: aas.Environment) -> PackageSnapshot:
    submodels = {
        submodel.id_short or submodel.id: dict(_walk(submodel.submodel_elements or [], ""))
        for submodel in environment.submodels or []
    }
    concepts = {cd.id: _concept_facts(cd) for cd in environment.concept_descriptions or []}
    return PackageSnapshot(submodels=submodels, concepts=concepts)


def _walk(
    elements: Iterable[aas.SubmodelElement], prefix: str
) -> Iterator[tuple[str, ElementFacts]]:
    for index, element in enumerate(elements):
        # SubmodelElementList items have no idShort (AASd-120); address them by position.
        name = element.id_short or f"[{index}]"
        path = f"{prefix}/{name}" if prefix else name
        yield path, _element_facts(element)
        yield from _walk(_children(element), path)


def _children(element: aas.SubmodelElement) -> list[aas.SubmodelElement]:
    if isinstance(element, aas.SubmodelElementCollection | aas.SubmodelElementList):
        return list(element.value or [])
    if isinstance(element, aas.Entity):
        return list(element.statements or [])
    return []


def _element_facts(element: aas.SubmodelElement) -> ElementFacts:
    value_type = getattr(element, "value_type", None)
    return ElementFacts(
        kind=type(element).__name__,
        semantic_id=_last_key(element.semantic_id),
        cardinality=next(
            (q.value or "" for q in element.qualifiers or [] if q.type == CARDINALITY_QUALIFIER),
            "",
        ),
        value_type=value_type.value if isinstance(value_type, aas.DataTypeDefXSD) else "",
        display_names=tuple((name.language, name.text) for name in element.display_name or []),
    )


def _last_key(reference: aas.Reference | None) -> str:
    return reference.keys[-1].value if reference and reference.keys else ""


def _concept_facts(concept: aas.ConceptDescription) -> ConceptFacts:
    iec = next(
        (
            spec.data_specification_content
            for spec in concept.embedded_data_specifications or []
            if isinstance(spec.data_specification_content, aas.DataSpecificationIEC61360)
        ),
        None,
    )
    if iec is None:
        return ConceptFacts(id_short=concept.id_short or "")
    return ConceptFacts(
        id_short=concept.id_short or "",
        preferred_names=tuple((name.language, name.text) for name in iec.preferred_name),
        unit=iec.unit or "",
        definitions=tuple((text.language, text.text) for text in iec.definition or []),
    )
