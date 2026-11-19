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
AddDocumentFn = Callable[[str, str, str | None], str]
ServeFn = Callable[[str, int], None]


def run(
    argv: Sequence[str],
    compare: CompareFn,
    import_: ImportFn,
    export: ExportFn,
    pdf: ExportFn,
    add_document: AddDocumentFn,
    serve: ServeFn | None = None,
    out: TextIO = sys.stdout,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "import":
            result = import_(args.workbook, args.output, args.submodel_id)
            print_import(result, args.output, out)
            return 1 if result.has_errors else 0
        if args.command == "serve":
            if serve is None:
                raise ValueError("the web app is not available")
            serve(args.host, args.port)
            return 0
        if args.command == "add-document":
            id_short = add_document(args.package, args.output, args.submodel)
            print(f"wrote {args.output}: added AsciiDoc submodel {id_short}", file=out)
            return 0
        if args.command in ("adoc", "pdf"):
            build = export if args.command == "adoc" else pdf
            document, main_file = build(args.package, args.output, args.submodel)
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

    web = commands.add_parser("serve", help="run the web app (ADR 0005-0007)")
    web.add_argument("--host", default="127.0.0.1", help="interface to listen on")
    web.add_argument("--port", type=int, default=8000)

    package_commands = (
        ("add-document", "add an IDTA starter document (ADR 0008)", "AASX file to write",
         "idShort of the data submodel, if there are several"),
        ("adoc", "export the AsciiDoc submodel of an AASX", "folder for the .adoc and its files",
         "idShort of the AsciiDoc submodel (default: by semanticId)"),
        ("pdf", "export the AsciiDoc submodel and build the PDF", "folder for .adoc, files and PDF",
         "idShort of the AsciiDoc submodel (default: by semanticId)"),
    )  # fmt: skip
    for name, help_text, output_help, submodel_help in package_commands:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("package", help="AASX package")
        command.add_argument("-o", "--output", required=True, help=output_help)
        command.add_argument("--submodel", help=submodel_help)

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
