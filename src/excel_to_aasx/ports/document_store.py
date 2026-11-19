from typing import Protocol

from excel_to_aasx.domain.document.nodes import DocSource
from excel_to_aasx.domain.document.render import RenderedDocument


class DocumentReader(Protocol):
    def read(self, source: str, submodel: str | None = None) -> DocSource:
        """The AsciiDoc submodel of a package. Raises `ValueError` if there is none."""
        ...


class DocumentWriter(Protocol):
    def write(self, target: str, document: RenderedDocument) -> str:
        """Write the document and its assets; returns the path of the main file."""
        ...
