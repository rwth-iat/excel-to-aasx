"""Command line. Use-cases arrive as callables from main.py."""

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from excel_to_aasx.domain.report import ComparisonReport, Mount

CompareFn = Callable[[str, str, Mount | None], ComparisonReport]


def run(argv: Sequence[str], compare: CompareFn, out: TextIO = sys.stdout) -> int:
    args = _parser().parse_args(argv)
    mount = Mount(args.submodel, args.mount) if args.submodel else None
    try:
        report = compare(args.expected, args.reference, mount)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    _print_report(report, out)
    return 1 if report.differences else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="excel-to-aasx")
    commands = parser.add_subparsers(dest="command", required=True)
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


def _print_report(report: ComparisonReport, out: TextIO) -> None:
    where = f"{report.mount.submodel}/{report.mount.path}".rstrip("/")
    print(
        f"reference mount: {where}\n"
        f"checked {report.elements_checked} elements, {report.concepts_checked} concepts: "
        f"{len(report.differences)} difference(s)",
        file=out,
    )
    for diff in report.differences:
        print(f"  {diff.path}  {diff.field}: {diff.expected!r} != {diff.actual!r}", file=out)
