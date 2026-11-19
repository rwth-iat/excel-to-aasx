from typing import Protocol

from excel_to_aasx.domain.importing.result import ImportResult, Issue


class PackageWriter(Protocol):
    def write(self, target: str, result: ImportResult) -> list[Issue]:
        """Write an AASX package. Returns metamodel verification findings (as warnings)."""
        ...
