"""Command line. Use-cases arrive as callables from main.py."""

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from excel_to_aasx.adapters.cli.report import print_comparison, print_export, print_import
from excel_to_aasx.domain.document.render import RenderedDocument
from excel_to_aasx.domain.importing.result import ImportResult
from excel_to_aasx.domain.report import ComparisonReport, Mount

CompareFn = Callable[[str, str, Mount | None], ComparisonReport]
ImportFn = Callable[[str, str, str | None], ImportResult]
ExportFn = Callable[[str, str, str | None], tuple[RenderedDocument, str]]


def run(
    argv: Sequence[str],
    compare: CompareFn,
    import_: ImportFn,
    export: ExportFn,
    out: TextIO = sys.stdout,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "import":
            result = import_(args.workbook, args.output, args.submodel_id)
            print_import(result, args.output, out)
            return 1 if result.has_errors else 0
        if args.command == "adoc":
            document, main_file = export(args.package, args.output, args.submodel)
            print_export(document, main_file, out)
            return 1 if any(i.severity == "error" for i in document.issues) else 0
        mount = Mount(args.submodel, args.mount) if args.submodel else None
        report = compare(args.expected, args.reference, mount)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print_comparison(report, out)
    return 1 if report.differences else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="excel-to-aasx")
    commands = parser.add_subparsers(dest="command", required=True)

    imp = commands.add_parser("import", help="convert a NAMUR SMT import workbook to AASX")
    imp.add_argument("workbook", help=".xlsx in the 'Import NAMUR SMTs' layout")
    imp.add_argument("-o", "--output", required=True, help="AASX file to write")
    imp.add_argument("--submodel-id", help="submodel id (default: derived, stable)")

    adoc = commands.add_parser("adoc", help="export the AsciiDoc submodel of an AASX")
    adoc.add_argument("package", help="AASX with a Package Explorer AsciiDoc submodel")
    adoc.add_argument("-o", "--output", required=True, help="folder for the .adoc and its files")
    adoc.add_argument(
        "--submodel", help="idShort of the AsciiDoc submodel (default: by semanticId)"
    )

    diff = commands.add_parser(
        "diff", help="check that REFERENCE contains every element and concept of EXPECTED"
    )
    diff.add_argument("expected", help="AASX with exactly one submodel, e.g. our import output")
    diff.add_argument("reference", help="AASX to check against, e.g. examples/*.aasx")
    diff.add_argument("--submodel", help="idShort of the reference submodel (default: auto)")
    diff.add_argument(
        "--mount", default="", help="container path inside --submodel, e.g. A/B (default: root)"
    )
    return parser
