"""Composition root: the only place that constructs adapters."""

import datetime
import os
import sys
import tempfile
from functools import partial
from pathlib import Path

from excel_to_aasx.adapters import cli
from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.aasx.document_submodel import AasxDocumentEditor
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.pdf import DockerPdfCompiler
from excel_to_aasx.adapters.pdf.diagram import DockerDiagramRenderer, RemoteDiagramRenderer
from excel_to_aasx.adapters.pdf.remote import RemotePdfCompiler
from excel_to_aasx.adapters.templates import load_frame
from excel_to_aasx.adapters.web import WebLimits, WebServices, Workspaces, create_app
from excel_to_aasx.app.add_document import add_document, has_document
from excel_to_aasx.app.build_pdf import build_pdf
from excel_to_aasx.app.compare_packages import compare_packages
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.app.import_workbook import import_workbook
from excel_to_aasx.app.open_upload import open_upload
from excel_to_aasx.app.render_diagram import render_diagram
from excel_to_aasx.ports.diagram_renderer import DiagramRenderer

MAX_PACKAGE_PART_BYTES = 200 * 1024 * 1024
MAX_WORKBOOK_BYTES = 200 * 1024 * 1024
# Pinned: the PDF layout depends on asciidoctor-pdf's version (ADR 0004).
ASCIIDOCTOR_IMAGE = "asciidoctor/docker-asciidoctor:1.108.1"
PDF_TIMEOUT_SECONDS = 300
DIAGRAM_TIMEOUT_SECONDS = 30
WORKSPACE_IDLE_SECONDS = 2 * 60 * 60
MAX_WORKSPACES = 200


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
        _pdf_compiler(),
    )
    editor = AasxDocumentEditor(MAX_PACKAGE_PART_BYTES)
    add = partial(_add_document, editor)
    opener = partial(open_upload, import_, add, partial(has_document, editor), export)
    compiler = _pdf_compiler()
    web = WebServices(
        open_upload=opener,
        compile_pdf=compiler.compile,
        render_diagram=partial(render_diagram, _diagram_renderer()),
    )
    serve = partial(_serve, web)
    return cli.run(
        sys.argv[1:],
        compare=compare,
        import_=import_,
        export=export,
        pdf=pdf,
        add_document=add,
        serve=serve,
    )


def _pdf_compiler() -> DockerPdfCompiler | RemotePdfCompiler:
    """The builder service when configured (ADR 0009), else a local container per build."""
    if url := os.environ.get("EXCEL_TO_AASX_BUILDER_URL"):
        return RemotePdfCompiler(url, PDF_TIMEOUT_SECONDS)
    return DockerPdfCompiler(ASCIIDOCTOR_IMAGE, PDF_TIMEOUT_SECONDS)


def _diagram_renderer() -> DiagramRenderer:
    """The diagram service, else the builder, else a container per diagram (ADR 0011)."""
    if url := os.environ.get("EXCEL_TO_AASX_DIAGRAM_URL") or os.environ.get(
        "EXCEL_TO_AASX_BUILDER_URL"
    ):
        return RemoteDiagramRenderer(url, DIAGRAM_TIMEOUT_SECONDS)
    return DockerDiagramRenderer(ASCIIDOCTOR_IMAGE, DIAGRAM_TIMEOUT_SECONDS)


def _serve(services: WebServices, host: str, port: int) -> None:
    import uvicorn

    root = Path(
        os.environ.get("EXCEL_TO_AASX_WORKSPACES") or Path(tempfile.gettempdir()) / "excel-to-aasx"
    )
    workspaces = Workspaces(root, idle_seconds=WORKSPACE_IDLE_SECONDS, max_count=MAX_WORKSPACES)
    uvicorn.run(create_app(services, workspaces, WebLimits()), host=host, port=port)


def _add_document(
    editor: AasxDocumentEditor, source: str, target: str, submodel: str | None
) -> str:
    return add_document(editor, load_frame, source, target, submodel, datetime.date.today())


if __name__ == "__main__":
    sys.exit(main())
