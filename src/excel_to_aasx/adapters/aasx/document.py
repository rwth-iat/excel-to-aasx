"""Read the Package Explorer AsciiDoc submodel of an AASX as DocNodes."""

import zipfile

import aas_core3_1.types as aas

from excel_to_aasx.adapters.aasx.package import load_environment, read_part
from excel_to_aasx.domain.document.nodes import (
    SUBMODEL_SEMANTIC_ID,
    DocNode,
    DocSource,
    asciidoc_function,
)

ARGS_EXTENSION = "ExportSmt.Args"
DEFAULT_LANGUAGE = "en"


class AasxDocumentReader:
    def __init__(self, max_part_bytes: int) -> None:
        self._max_part_bytes = max_part_bytes

    def read(self, source: str, submodel: str | None = None) -> DocSource:
        environment = load_environment(source, self._max_part_bytes)
        chosen = _pick(environment, submodel)
        with zipfile.ZipFile(source) as package:
            nodes = tuple(
                _node(element, package, self._max_part_bytes)
                for element in chosen.submodel_elements or []
            )
        return DocSource(chosen.id_short or "", nodes)


def _pick(environment: aas.Environment, id_short: str | None) -> aas.Submodel:
    for submodel in environment.submodels or []:
        if id_short is not None and submodel.id_short == id_short:
            return submodel
        if id_short is None and _last_key(submodel.semantic_id) == SUBMODEL_SEMANTIC_ID:
            return submodel
    wanted = (
        f"submodel '{id_short}'" if id_short else f"submodel with semanticId {SUBMODEL_SEMANTIC_ID}"
    )
    raise ValueError(f"no {wanted} in package")


def _node(element: aas.SubmodelElement, package: zipfile.ZipFile, limit: int) -> DocNode:
    content: bytes | None = None
    file_path = ""
    if isinstance(element, aas.Blob):
        content = element.value
    if isinstance(element, aas.File) and element.value:
        file_path = element.value
        content = read_part(package, element.value, limit)
    children: list[aas.SubmodelElement] = []
    if isinstance(element, aas.SubmodelElementCollection | aas.SubmodelElementList):
        children = list(element.value or [])
    return DocNode(
        kind=type(element).__name__,
        id_short=element.id_short or "",
        function=asciidoc_function(_last_key(element.semantic_id)),
        title=_default_text(element.description),
        args=next(
            (x.value or "" for x in element.extensions or [] if x.name == ARGS_EXTENSION), ""
        ),
        content=content,
        content_type=getattr(element, "content_type", None) or "",
        file_path=file_path,
        reference=_keys(element.value) if isinstance(element, aas.ReferenceElement) else (),
        children=tuple(_node(child, package, limit) for child in children),
    )


def _default_text(texts: list[aas.LangStringTextType] | None) -> str:
    """GetDefaultString: the default language, else the first entry."""
    if not texts:
        return ""
    for text in texts:
        if text.language.strip().lower() == DEFAULT_LANGUAGE:
            return text.text
    return texts[0].text


def _keys(reference: aas.Reference | None) -> tuple[str, ...]:
    return tuple(key.value for key in reference.keys) if reference else ()


def _last_key(reference: aas.Reference | None) -> str:
    return reference.keys[-1].value if reference and reference.keys else ""
