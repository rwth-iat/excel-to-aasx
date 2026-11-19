from collections.abc import Callable
from pathlib import PurePath

from excel_to_aasx.domain.document.opened import OpenedDocument
from excel_to_aasx.domain.document.render import RenderedDocument
from excel_to_aasx.domain.importing.result import ImportResult, Issue

ImportFn = Callable[[str, str, str | None], ImportResult]
AddDocumentFn = Callable[[str, str, str | None], str]
HasDocumentFn = Callable[[str], bool]
ExportFn = Callable[[str, str, str | None], tuple[RenderedDocument, str]]


def open_upload(
    import_: ImportFn,
    add_document: AddDocumentFn,
    has_document: HasDocumentFn,
    export: ExportFn,
    source: str,
    folder: str,
) -> OpenedDocument:
    """Upload (.xlsx or .aasx) -> package with a document -> exported AsciiDoc folder.

    An Excel workbook is imported first; a package without a document gets the starter
    document (ADR 0008). Raises `ValueError` for unreadable input.
    """
    issues: list[Issue] = []
    package = source
    if PurePath(source).suffix.lower() == ".xlsx":
        package = str(PurePath(folder) / "import.aasx")
        issues.extend(import_(source, package, None).issues)
    if not has_document(package):
        with_document = str(PurePath(folder) / "package.aasx")
        add_document(package, with_document, None)
        package = with_document
    document, main_file = export(package, str(PurePath(folder) / "doc"), None)
    issues.extend(document.issues)
    return OpenedDocument(package, main_file, document, issues)
