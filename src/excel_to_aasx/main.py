"""Composition root: the only place that constructs adapters."""

import sys
from functools import partial

from excel_to_aasx.adapters import cli
from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.pdf import DockerPdfCompiler
from excel_to_aasx.app.build_pdf import build_pdf
from excel_to_aasx.app.compare_packages import compare_packages
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.app.import_workbook import import_workbook

MAX_PACKAGE_PART_BYTES = 200 * 1024 * 1024
MAX_WORKBOOK_BYTES = 200 * 1024 * 1024
# Pinned: the PDF layout depends on asciidoctor-pdf's version (ADR 0004).
ASCIIDOCTOR_IMAGE = "asciidoctor/docker-asciidoctor:1.108.1"
PDF_TIMEOUT_SECONDS = 300


def main() -> int:
    compare = partial(compare_packages, AasxPackageReader(max_part_bytes=MAX_PACKAGE_PART_BYTES))
    import_ = partial(
        import_workbook,
        ExcelSheetReader(max_uncompressed_bytes=MAX_WORKBOOK_BYTES),
        AasxPackageWriter(),
    )
    export = partial(
        export_document, AasxDocumentReader(MAX_PACKAGE_PART_BYTES), FolderDocumentWriter()
    )
    pdf = partial(
        build_pdf,
        AasxDocumentReader(MAX_PACKAGE_PART_BYTES),
        FolderDocumentWriter(),
        DockerPdfCompiler(ASCIIDOCTOR_IMAGE, PDF_TIMEOUT_SECONDS),
    )
    return cli.run(sys.argv[1:], compare=compare, import_=import_, export=export, pdf=pdf)


if __name__ == "__main__":
    sys.exit(main())
