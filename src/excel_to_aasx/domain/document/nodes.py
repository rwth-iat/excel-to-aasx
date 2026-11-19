"""The AsciiDoc submodel as the export sees it."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from excel_to_aasx.domain.document.tables.model import Element

FUNCTION_PREFIX = "http://admin-shell.io/aasx-package-explorer/functions/asciidoc/"
SUBMODEL_SEMANTIC_ID = f"{FUNCTION_PREFIX[:-1]}/1/0"


@dataclass(frozen=True)
class DocNode:
    kind: str  # AAS element type name, e.g. "Blob"
    id_short: str
    function: str = ""  # e.g. "heading1"; "" when the semanticId is no AsciiDoc function
    title: str = ""  # description in the default language
    args: str = ""  # raw JSON of the `ExportSmt.Args` extension
    content: bytes | None = None  # Blob value, or the package file a File points to
    content_type: str = ""
    file_path: str = ""  # File value
    reference: tuple[str, ...] = ()  # ReferenceElement key values
    children: tuple["DocNode", ...] = field(default_factory=tuple)

    def with_children(self, children: tuple["DocNode", ...]) -> "DocNode":
        return replace(self, children=children)


@dataclass(frozen=True)
class DocSource:
    submodel_id_short: str
    nodes: tuple[DocNode, ...]
    # Every submodel of the package by id, for generated tables and diagrams.
    models: Mapping[str, Element] = field(default_factory=dict)


def asciidoc_function(semantic_id: str) -> str:
    """`.../functions/asciidoc/heading1/1/0` -> `heading1`. PE ignores key types here too."""
    if not semantic_id.startswith(FUNCTION_PREFIX):
        return ""
    name, _, version = semantic_id[len(FUNCTION_PREFIX) :].partition("/")
    return name if version == "1/0" else ""
