from collections import Counter
from typing import TextIO

from excel_to_aasx.domain.importing.result import ImportResult
from excel_to_aasx.domain.report import ComparisonReport


def print_import(result: ImportResult, target: str, out: TextIO) -> None:
    counts = Counter(issue.severity for issue in result.issues)
    print(
        f"wrote {target}: submodel {result.submodel.id_short} ({result.submodel.id}), "
        f"{len(result.concepts)} concepts; "
        f"{counts['error']} error(s), {counts['warning']} warning(s)",
        file=out,
    )
    for issue in sorted(result.issues, key=lambda i: i.severity != "error"):
        print(f"  {issue.severity:7} {issue.location}: {issue.message}", file=out)


def print_comparison(report: ComparisonReport, out: TextIO) -> None:
    where = f"{report.mount.submodel}/{report.mount.path}".rstrip("/")
    print(
        f"reference mount: {where}\n"
        f"checked {report.elements_checked} elements, {report.concepts_checked} concepts: "
        f"{len(report.differences)} difference(s)",
        file=out,
    )
    for diff in report.differences:
        print(f"  {diff.path}  {diff.field}: {diff.expected!r} != {diff.actual!r}", file=out)
