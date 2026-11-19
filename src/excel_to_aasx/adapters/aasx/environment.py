"""Turn an import result into aas-core3.1 objects (spec sections 5-6)."""

import aas_core3_1.types as aas

from excel_to_aasx.domain.importing.build import generated_id
from excel_to_aasx.domain.importing.model import Concept, Element, LangText, SubmodelDraft
from excel_to_aasx.domain.importing.result import ImportResult

AAS_ID_TEMPLATE = "www.example.com/ids/aas/DDDD_DDDD_DDDD_DDDD"
ASSET_ID_TEMPLATE = "www.example.com/ids/asset/DDDD_DDDD_DDDD_DDDD"
CARDINALITY_QUALIFIER = "SMT/Cardinality"
IEC61360 = "http://admin-shell.io/DataSpecificationTemplates/DataSpecificationIEC61360/3/0"

_SIMPLE_KINDS: dict[str, type] = {
    "MultiLanguageProperty": aas.MultiLanguageProperty,
    "File": aas.File,
    "Blob": aas.Blob,
    "ReferenceElement": aas.ReferenceElement,
    "RelationshipElement": aas.RelationshipElement,
    "AnnotatedRelationshipElement": aas.AnnotatedRelationshipElement,
    "Capability": aas.Capability,
    "Entity": aas.Entity,
    "Operation": aas.Operation,
}


def environment_of(result: ImportResult) -> aas.Environment:
    submodel = _submodel(result.submodel)
    shell = aas.AssetAdministrationShell(
        id=generated_id(AAS_ID_TEMPLATE, submodel.id),
        id_short=f"{submodel.id_short}_AAS" if submodel.id_short else None,
        asset_information=aas.AssetInformation(
            asset_kind=aas.AssetKind.TYPE,
            global_asset_id=generated_id(ASSET_ID_TEMPLATE, submodel.id),
        ),
        submodels=[_model_ref(aas.KeyTypes.SUBMODEL, submodel.id)],
    )
    return aas.Environment(
        asset_administration_shells=[shell],
        submodels=[submodel],
        concept_descriptions=[_concept(c) for c in result.concepts] or None,
    )


def _submodel(draft: SubmodelDraft) -> aas.Submodel:
    return aas.Submodel(
        id=draft.id,
        id_short=draft.id_short or None,
        semantic_id=_global_ref(draft.semantic_id),
        description=_texts(aas.LangStringTextType, draft.description),
        kind=aas.ModellingKind.TEMPLATE,
        submodel_elements=[_element(e) for e in draft.elements] or None,
    )


def _element(draft: Element) -> aas.SubmodelElement:
    common = {
        "id_short": draft.id_short or None,
        "semantic_id": _global_ref(draft.semantic_id),
        "display_name": _texts(aas.LangStringNameType, draft.display_names),
        "description": _texts(aas.LangStringTextType, draft.description),
        "qualifiers": _cardinality(draft.cardinality),
    }
    children = [_element(child) for child in draft.children] or None
    if draft.kind == "SubmodelElementCollection":
        return aas.SubmodelElementCollection(value=children, **common)
    if draft.kind == "SubmodelElementList":
        # PE creates lists with typeValueListElement = SubmodelElement.
        return aas.SubmodelElementList(
            type_value_list_element=aas.AASSubmodelElements.SUBMODEL_ELEMENT,
            value=children,
            **common,
        )
    if draft.kind in ("Property", "Range"):
        value_type = aas.DataTypeDefXSD(draft.value_type or "xs:string")
        cls = aas.Property if draft.kind == "Property" else aas.Range
        return cls(value_type=value_type, **common)
    return _SIMPLE_KINDS[draft.kind](**common)


def _concept(concept: Concept) -> aas.ConceptDescription:
    content = aas.DataSpecificationIEC61360(
        preferred_name=_texts(aas.LangStringPreferredNameTypeIEC61360, concept.preferred_names)
        or [aas.LangStringPreferredNameTypeIEC61360("en", concept.id_short or concept.id)],
        definition=_texts(aas.LangStringDefinitionTypeIEC61360, concept.definitions),
        unit=concept.unit or None,
    )
    spec = aas.EmbeddedDataSpecification(
        data_specification=_external_ref(IEC61360),
        data_specification_content=content,
    )
    return aas.ConceptDescription(
        id=concept.id, id_short=concept.id_short or None, embedded_data_specifications=[spec]
    )


def _texts(cls, pairs: tuple[LangText, ...] | list[LangText]):
    return [cls(language, text) for language, text in pairs] or None


def _cardinality(value: str) -> list[aas.Qualifier] | None:
    if not value:
        return None
    return [
        aas.Qualifier(type=CARDINALITY_QUALIFIER, value_type=aas.DataTypeDefXSD.STRING, value=value)
    ]


def _global_ref(value: str) -> aas.Reference | None:
    return _external_ref(value) if value else None


def _external_ref(value: str) -> aas.Reference:
    return aas.Reference(
        type=aas.ReferenceTypes.EXTERNAL_REFERENCE,
        keys=[aas.Key(type=aas.KeyTypes.GLOBAL_REFERENCE, value=value)],
    )


def _model_ref(key_type: aas.KeyTypes, value: str) -> aas.Reference:
    return aas.Reference(
        type=aas.ReferenceTypes.MODEL_REFERENCE, keys=[aas.Key(type=key_type, value=value)]
    )
