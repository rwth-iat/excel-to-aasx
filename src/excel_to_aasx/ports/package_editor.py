from collections.abc import Mapping
from typing import Protocol

from excel_to_aasx.domain.document.nodes import DocNode
from excel_to_aasx.domain.document.starter import Frame
from excel_to_aasx.domain.document.tables.model import Element


class PackageEditor(Protocol):
    def models(self, source: str) -> Mapping[str, Element]:
        """Every submodel of the package by id."""
        ...

    def add_document(
        self, source: str, target: str, nodes: tuple[DocNode, ...], data_id: str
    ) -> str:
        """Write `source` plus an AsciiDoc submodel to `target`; returns its idShort."""
        ...


class FrameSource(Protocol):
    def __call__(self, name: str) -> Frame: ...
