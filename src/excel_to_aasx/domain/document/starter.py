"""Build a starter AsciiDoc submodel for a data submodel (ADR 0008).

The frame (cover, front matter, annex) is text from a template; the chapter about the
submodel is generated: a UML overview and one table per collection.
"""

import datetime
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from excel_to_aasx.domain.document.nodes import DocNode
from excel_to_aasx.domain.document.tables.model import Element
from excel_to_aasx.domain.document.tables.placeholders import ABBREVIATIONS

NUMBER_PLACEHOLDER = "[IDTA number]"
TABLE_NOTE = "The table convention is explained in Annex A.2."
_CONTENT_TYPES = {
    ".yml": "text/plain", ".css": "text/plain", ".png": "image/png", ".svg": "image/svg+xml",
    ".ttf": "font/ttf", ".jpg": "image/jpeg", ".gif": "image/gif",
}  # fmt: skip


@dataclass(frozen=True)
class Frame:
    parts: Mapping[str, str]  # "cover", "front", "back"
    assets: Mapping[str, bytes]  # file name -> data


def starter_nodes(
    data: Element, submodel_id: str, frame: Frame, today: datetime.date
) -> tuple[DocNode, ...]:
    values = {
        "number": NUMBER_PLACEHOLDER,
        "title": _safe(data.id_short),
        "idShort": _safe(data.id_short),
        "date": today.isoformat(),
        "month": today.strftime("%B %Y"),
    }
    text = {name: _fill(part, values) for name, part in frame.parts.items()}
    return (
        DocNode("SubmodelElementCollection", "Fixed_content", children=tuple(_assets(frame))),
        _blob("coverpage", "CoverPage", text.get("cover", "")),
        _blob("textblock", "Front_matter", text.get("front", "")),
        DocNode(
            "SubmodelElementCollection",
            "Submodel_chapter",
            children=tuple(_chapter(data, submodel_id)),
        ),
        _blob("textblock", "Back_matter", text.get("back", "")),
    )


def _chapter(data: Element, submodel_id: str) -> Iterator[DocNode]:
    name = _safe(data.id_short)
    yield _blob("heading1", "Heading", f"Submodel {name}")
    yield _blob("heading2", "Approach", "Approach")
    yield _blob(
        "textblock", "Approach_text",
        "*TODO:* Describe the approach and the overall structure of the Submodel.\n\n"
        "The following UML diagram gives an overview of the Submodel (see <<UML_Submodel>>).",
    )  # fmt: skip
    uml_args = {"depth": 2, "uml": {"LimitInitialValue": 0, "NoAssociationNames": True}}
    yield _reference(
        "generate-uml",
        "UML_Submodel",
        (submodel_id,),
        uml_args,
        f"UML overview of the Submodel {name}",
    )
    yield _blob("heading2", "Attributes", f"Attributes of the Submodel {name}")
    yield _blob(
        "textblock", "Attributes_text",
        "For the Submodel, the SubmodelElements are described as follows "
        f"(see <<Table_Submodel>>). {TABLE_NOTE}",
    )  # fmt: skip
    yield _reference(
        "generate-tables",
        "Table_Submodel",
        (submodel_id,),
        {"depth": 1},
        f"Table for Submodel {name}",
    )
    for path, container in _containers(data.children, ()):
        yield _section(submodel_id, path, container)


def _section(submodel_id: str, path: tuple[str, ...], container: Element) -> DocNode:
    """One collection per section: idShorts must be unique among siblings (AASd-022)."""
    label = _label(path)
    table_id = "Table_" + re.sub(r"[^a-zA-Z0-9_]", "_", "_".join(path))
    kind = ABBREVIATIONS.get(container.kind, container.kind)
    heading = _blob("heading2", "Heading", f"SubmodelElements of {label}")
    text = _blob(
        "textblock", "Text",
        f"*TODO:* Describe the purpose of {label}.\n\n"
        f"For the {kind} {label}, the SubmodelElements are described as follows "
        f"(see <<{table_id}>>). {TABLE_NOTE}",
    )  # fmt: skip
    table = _reference(
        "generate-tables", table_id, (submodel_id, *path), {"depth": 1}, f"Table for {kind} {label}"
    )
    section_id = "Section_" + table_id.removeprefix("Table_")
    return DocNode("SubmodelElementCollection", section_id, children=(heading, text, table))


def _containers(
    elements: tuple[Element, ...], prefix: tuple[str, ...]
) -> Iterator[tuple[tuple[str, ...], Element]]:
    """Pre-order: every collection or list with children; list items are addressed by index."""
    for index, element in enumerate(elements):
        key = element.id_short or str(index)
        path = (*prefix, key)
        if (
            element.kind in ("SubmodelElementCollection", "SubmodelElementList")
            and element.children
        ):
            yield path, element
            yield from _containers(element.children, path)


def _assets(frame: Frame) -> Iterator[DocNode]:
    for name, data in sorted(frame.assets.items()):
        stem, dot, extension = name.rpartition(".")
        id_short = f"{stem}_dot_{extension}" if dot else name
        content_type = _CONTENT_TYPES.get(f".{extension.lower()}", "application/octet-stream")
        yield DocNode(
            "Blob",
            re.sub(r"[^a-zA-Z0-9_-]", "_", id_short),
            "imagefile",
            args=json.dumps({"noLink": True}),
            content=data,
            content_type=content_type,
        )


def _blob(function: str, id_short: str, text: str) -> DocNode:
    return DocNode(
        "Blob", id_short, function, content=text.encode("utf-8"), content_type="text/markdown"
    )


def _reference(
    function: str, id_short: str, keys: tuple[str, ...], args: dict, title: str
) -> DocNode:
    return DocNode(
        "ReferenceElement", id_short, function, title=title, args=json.dumps(args), reference=keys
    )


def _label(path: tuple[str, ...]) -> str:
    """`(..., "ProductImages", "0")` -> `ProductImages[0]`: the last name, plus list positions."""
    name = ""
    for key in path:
        name = f"{name}[{key}]" if key.isdigit() else key
    return _safe(name)


def _fill(text: str, values: Mapping[str, str]) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), text)


def _safe(text: str) -> str:
    """Values from the workbook go into AsciiDoc text: no line breaks, no attribute references."""
    return re.sub(r"\s+", " ", text).replace("{", "\\{").strip()
