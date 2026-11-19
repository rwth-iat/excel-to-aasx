"""Command line. Use-cases arrive as callables from main.py."""

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from excel_to_aasx.adapters.cli.report import print_comparison, print_import
from excel_to_aasx.domain.importing.result import ImportResult
from excel_to_aasx.domain.report import ComparisonReport, Mount

CompareFn = Callable[[str, str, Mount | None], ComparisonReport]
ImportFn = Callable[[str, str, str | None], ImportResult]


def run(
    argv: Sequence[str], compare: CompareFn, import_: ImportFn, out: TextIO = sys.stdout
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "import":
            result = import_(args.workbook, args.output, args.submodel_id)
            print_import(result, args.output, out)
            return 1 if result.has_errors else 0
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
