from typing import Protocol

from excel_to_aasx.domain.importing.model import Sheet


class SheetReader(Protocol):
    def read(self, source: str) -> list[Sheet]:
        """Every worksheet, in order. Raises `ValueError` when `source` is not readable."""
        ...
