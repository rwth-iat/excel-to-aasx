from excel_to_aasx.domain.document.render import RenderedDocument, render_document
from excel_to_aasx.domain.importing.result import Issue
from excel_to_aasx.ports.document_store import DocumentReader, DocumentWriter
from excel_to_aasx.ports.pdf_compiler import PdfCompiler


def build_pdf(
    reader: DocumentReader,
    writer: DocumentWriter,
    compiler: PdfCompiler,
    source: str,
    target: str,
    submodel: str | None,
) -> tuple[RenderedDocument, str]:
    """AASX -> folder with .adoc, assets and the compiled PDF. Returns document and PDF path."""
    document = render_document(reader.read(source, submodel))
    main_file = writer.write(target, document)
    pdf, messages = compiler.compile(main_file)
    document.issues.extend(Issue("warning", "asciidoctor-pdf", message) for message in messages)
    return document, pdf
