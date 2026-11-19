"""Flatten the AsciiDoc submodel into the order it is written (ExportSmtToFile, first loop)."""

from collections.abc import Iterator, Sequence
from dataclasses import replace

from excel_to_aasx.domain.document.args import parse_args
from excel_to_aasx.domain.document.nodes import DocNode
from excel_to_aasx.domain.importing.result import Issue

ITERATE = "iterate-list"


def linearize(nodes: Sequence[DocNode], issues: list[Issue]) -> Iterator[DocNode]:
    """Pre-order; an `iterate-list` collection repeats its contents once per `itemsA` entry."""
    for node in nodes:
        if node.function == ITERATE and node.kind == "SubmodelElementCollection":
            yield from _iterate(node, issues)
            continue
        if node.function:
            yield node
        yield from linearize(node.children, issues)


def _iterate(node: DocNode, issues: list[Issue]) -> Iterator[DocNode]:
    try:
        args = parse_args(node.args)
    except ValueError as error:
        issues.append(Issue("error", node.id_short, str(error)))
        return
    if not args.items.get("A"):
        issues.append(Issue("error", node.id_short, "iterate-list without ExportSmt.Args.itemsA"))
        return
    for index in range(len(args.items["A"])):
        values = {
            f"%ITEM{letter}%": items[index] if index < len(items) else ""
            for letter, items in args.items.items()
        }
        for inner in _all(node.children):
            if inner.function:
                yield _substitute(inner, values)


def _all(nodes: Sequence[DocNode]) -> Iterator[DocNode]:
    for node in nodes:
        yield node
        yield from _all(node.children)


def _substitute(node: DocNode, values: dict[str, str]) -> DocNode:
    """CopyWithItemPlaceholders. PE replaces only one placeholder per text; we replace all."""

    def text(value: str) -> str:
        for placeholder, item in values.items():
            value = value.replace(placeholder, item)
        return value

    content = node.content
    if content is not None:
        for placeholder, item in values.items():
            content = content.replace(placeholder.encode(), item.encode())
    return replace(
        node,
        id_short=text(node.id_short),
        title=text(node.title),
        content=content,
        reference=tuple(text(key) for key in node.reference),
    )
