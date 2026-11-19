"""Write the AsciiDoc text and collect its files (ExportSmtToFile, second loop)."""

import re
from dataclasses import dataclass, field

from excel_to_aasx.domain.document.args import ExportArgs, parse_args
from excel_to_aasx.domain.document.assets import (
    asset_name,
    blob_bytes,
    guess_extension,
    is_text_content_type,
    safe_file_name,
)
from excel_to_aasx.domain.document.linearize import linearize
from excel_to_aasx.domain.document.nodes import DocNode, DocSource
from excel_to_aasx.domain.importing.result import Issue

HEADINGS = {"heading1": "== ", "heading2": "=== ", "heading3": "==== ", "heading4": "===== "}
GENERATED = {
    "generate-tables": "table",
    "generate-uml": "UML diagram",
    "generate-enum-table": "enum table",
}


@dataclass
class RenderedDocument:
    file_name: str
    text: str = ""
    assets: dict[str, bytes] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)


def render_document(source: DocSource) -> RenderedDocument:
    document = RenderedDocument(f"{_friendly(source.submodel_id_short) or 'index'}.adoc")
    lines: list[str] = []
    for node in list(linearize(source.nodes, document.issues)):
        if node.kind == "Blob" and node.function in ("textblock", "coverpage", *HEADINGS):
            _text_block(node, lines)
        elif node.kind in ("Blob", "File") and node.function == "imagefile":
            _asset(node, lines, document)
        elif node.kind == "ReferenceElement" and node.function in GENERATED:
            _not_generated_yet(node, lines, document)
    document.text = "\n".join(lines) + "\n"
    return document


def _text_block(node: DocNode, lines: list[str]) -> None:
    if not node.content:
        return
    prefix = HEADINGS.get(node.function, "")
    if prefix:
        lines.append("")
    # Blob texts carry CRLF from Windows editors; the output uses LF throughout.
    text = node.content.decode("utf-8", errors="replace").replace("\r\n", "\n")
    lines.append(prefix + text)


def _asset(node: DocNode, lines: list[str], document: RenderedDocument) -> None:
    args = _args(node, document)
    if node.content is None:
        document.issues.append(Issue("error", node.id_short, "no image data found"))
        return
    if node.kind == "File":
        data = node.content
        extension = re.search(r"\.[^./\\]*$", node.file_path)
        extension_text = extension.group(0) if extension else ""
    else:
        data = blob_bytes(node.content, node.content_type)
        is_text = is_text_content_type(node.content_type)
        extension_text = ".txt" if is_text else guess_extension(data)
    name = asset_name(node.id_short, extension_text) if node.id_short else f"image{extension_text}"
    if args.file_name:
        name = safe_file_name(args.file_name)
        if name != args.file_name:
            document.issues.append(
                Issue("warning", node.id_short, f"fileName '{args.file_name}' changed to '{name}'")
            )
    document.assets[name] = data
    if not args.no_link:
        attributes = _link_attributes(args, node.title)
        lines.extend(["", f'image::{name}[id="{_friendly(node.id_short)}", {attributes}]', ""])


def _link_attributes(args: ExportArgs, title: str) -> str:
    """EvalLinkArguments."""
    text = ""
    if args.width is not None:
        text += f',width="{args.width:.1f}%"'
    if title:
        text += ',title="{}"'.format(title.replace('"', '\\"'))
    return text.strip(",")


def _not_generated_yet(node: DocNode, lines: list[str], document: RenderedDocument) -> None:
    what = GENERATED[node.function]
    lines.extend(
        ["", f"// {what} '{node.id_short}' from {'/'.join(node.reference)}: not generated yet", ""]
    )
    document.issues.append(
        Issue("warning", node.id_short, f"{what} generation is not implemented yet")
    )


def _args(node: DocNode, document: RenderedDocument) -> ExportArgs:
    try:
        return parse_args(node.args)
    except ValueError as error:
        document.issues.append(Issue("warning", node.id_short, f"{error}; ignored"))
        return ExportArgs()


def _friendly(text: str) -> str:
    """AdminShellUtil.FilterFriendlyName with its default filter."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", text)
