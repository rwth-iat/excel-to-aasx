"""Turn DocNodes into a Package Explorer AsciiDoc submodel and add it to a package."""

import aas_core3_1.types as aas

from excel_to_aasx.adapters.aasx.package import load_environment, replace_environment
from excel_to_aasx.adapters.aasx.table_model import table_models
from excel_to_aasx.domain.document.files.encoding import blob_value
from excel_to_aasx.domain.document.nodes import FUNCTION_PREFIX, SUBMODEL_SEMANTIC_ID, DocNode
from excel_to_aasx.domain.document.tables.model import Element
from excel_to_aasx.domain.importing.build import generated_id

ARGS_EXTENSION = "ExportSmt.Args"
SUBMODEL_ID_TEMPLATE = "www.example.com/ids/sm/DDDD_DDDD_DDDD_DDDD"


class AasxDocumentEditor:
    def __init__(self, max_part_bytes: int) -> None:
        self._limit = max_part_bytes

    def models(self, source: str) -> dict[str, Element]:
        return table_models(load_environment(source, self._limit))

    def add_document(
        self, source: str, target: str, nodes: tuple[DocNode, ...], data_id: str
    ) -> str:
        """Returns the idShort of the added AsciiDoc submodel."""
        environment = load_environment(source, self._limit)
        data = next((s for s in environment.submodels or [] if s.id == data_id), None)
        if data is None:
            raise ValueError(f"no submodel with id {data_id}")
        id_short = "AsciiDoc_" + "".join(
            c if c.isalnum() or c == "_" else "_" for c in data.id_short or "Submodel"
        )
        document = aas.Submodel(
            id=generated_id(SUBMODEL_ID_TEMPLATE, f"{data_id}/asciidoc"),
            id_short=id_short,
            semantic_id=_global(SUBMODEL_SEMANTIC_ID),
            submodel_elements=[_element(node, data) for node in nodes],
        )
        environment.submodels = [*(environment.submodels or []), document]
        for shell in environment.asset_administration_shells or []:
            if any(ref.keys[0].value == data_id for ref in shell.submodels or []):
                shell.submodels = [
                    *(shell.submodels or []),
                    _model_ref([(aas.KeyTypes.SUBMODEL, document.id)]),
                ]
        replace_environment(source, target, environment, self._limit)
        return id_short


def _element(node: DocNode, data: aas.Submodel) -> aas.SubmodelElement:
    common = {
        "id_short": node.id_short,
        "semantic_id": _global(f"{FUNCTION_PREFIX}{node.function}/1/0") if node.function else None,
        "description": [aas.LangStringTextType("en", node.title)] if node.title else None,
        "extensions": [aas.Extension(name=ARGS_EXTENSION, value=node.args)] if node.args else None,
    }
    if node.kind == "Blob":
        return aas.Blob(
            content_type=node.content_type or None,
            value=blob_value(node.content or b"", node.content_type),
            **common,
        )
    if node.kind == "ReferenceElement":
        return aas.ReferenceElement(value=_model_ref(_typed_keys(data, node.reference)), **common)
    children = [_element(child, data) for child in node.children]
    return aas.SubmodelElementCollection(value=children or None, **common)


def _typed_keys(data: aas.Submodel, values: tuple[str, ...]) -> list[tuple[aas.KeyTypes, str]]:
    """Key types follow the elements the path walks through, as ModelReferences require."""
    keys = [(aas.KeyTypes.SUBMODEL, values[0])]
    children: list[aas.SubmodelElement] = list(data.submodel_elements or [])
    for value in values[1:]:
        if value.isdigit() and int(value) < len(children) and not children[int(value)].id_short:
            element = children[int(value)]
        else:
            element = next((c for c in children if c.id_short == value), None)
        if element is None:
            raise ValueError(f"reference path not found: {'/'.join(values)}")
        keys.append((aas.KeyTypes(type(element).__name__), value))
        children = _children(element)
    return keys


def _children(element: aas.SubmodelElement) -> list[aas.SubmodelElement]:
    if isinstance(element, aas.SubmodelElementCollection | aas.SubmodelElementList):
        return list(element.value or [])
    if isinstance(element, aas.Entity):
        return list(element.statements or [])
    return []


def _model_ref(keys: list[tuple[aas.KeyTypes, str]]) -> aas.Reference:
    return aas.Reference(
        type=aas.ReferenceTypes.MODEL_REFERENCE,
        keys=[aas.Key(type=kind, value=value) for kind, value in keys],
    )


def _global(value: str) -> aas.Reference:
    return aas.Reference(
        type=aas.ReferenceTypes.EXTERNAL_REFERENCE,
        keys=[aas.Key(type=aas.KeyTypes.GLOBAL_REFERENCE, value=value)],
    )
