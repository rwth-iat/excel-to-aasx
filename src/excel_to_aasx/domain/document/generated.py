"""Parts generated from the target submodel: tables now; UML and enum tables later."""

import json

from excel_to_aasx.domain.document.args import ExportArgs, parse_args
from excel_to_aasx.domain.document.nodes import DocNode, DocSource
from excel_to_aasx.domain.document.tables.model import resolve
from excel_to_aasx.domain.document.tables.preset import SMT_ASCIIDOC_PRESET, TablePreset
from excel_to_aasx.domain.document.tables.writer import TableRequest, write_table
from excel_to_aasx.domain.importing.result import Issue

NOT_YET = {"generate-uml": "UML diagram", "generate-enum-table": "enum table"}


class Generator:
    """Keeps the table preset: a `tablerecord` blob replaces it for all later tables."""

    def __init__(self, source: DocSource, issues: list[Issue]) -> None:
        self._source = source
        self._issues = issues
        self._preset: TablePreset = SMT_ASCIIDOC_PRESET

    def table_record(self, node: DocNode) -> None:
        if not node.content:
            return
        try:
            self._preset = TablePreset.from_record(json.loads(node.content.decode("utf-8")))
        except (ValueError, UnicodeDecodeError, AttributeError) as error:
            self._issues.append(Issue("error", node.id_short, f"table record ignored: {error}"))

    def lines(self, node: DocNode) -> list[str]:
        if node.function in NOT_YET:
            what = NOT_YET[node.function]
            self._issues.append(
                Issue("warning", node.id_short, f"{what} generation is not implemented yet")
            )
            return [
                "",
                f"// {what} '{node.id_short}' from {'/'.join(node.reference)}: not generated yet",
                "",
            ]
        return self._table(node)

    def _table(self, node: DocNode) -> list[str]:
        args = self._args(node)
        located = resolve(self._source.models, node.reference)
        if located is None:
            self._issues.append(
                Issue("error", node.id_short, f"table target not found: {'/'.join(node.reference)}")
            )
            return []
        if args.depth != 1:
            self._issues.append(
                Issue(
                    "warning",
                    node.id_short,
                    f"table depth {args.depth} not supported; wrote depth 1",
                )
            )
        title = node.title.replace('"', '\\"') if node.title else ""
        request = TableRequest(
            located.element, located.parent, node.id_short, title, args.column_widths
        )
        table = write_table(self._preset, request)
        return ["", f"// Table generated from {'/'.join(node.reference)}", "", *table, ""]

    def _args(self, node: DocNode) -> ExportArgs:
        try:
            return parse_args(node.args)
        except ValueError as error:
            self._issues.append(Issue("warning", node.id_short, f"{error}; ignored"))
            return ExportArgs()
