from excel_to_aasx.domain.document.render import RenderedDocument, render_document
from excel_to_aasx.ports.document_store import DocumentReader, DocumentWriter


def export_document(
    reader: DocumentReader, writer: DocumentWriter, source: str, target: str, submodel: str | None
) -> tuple[RenderedDocument, str]:
    """AASX -> folder with the .adoc file and its assets. Returns the document and main path."""
    document = render_document(reader.read(source, submodel))
    return document, writer.write(target, document)
