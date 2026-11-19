from typing import Protocol

from excel_to_aasx.domain.snapshot import PackageSnapshot


class PackageReader(Protocol):
    def read(self, source: str) -> PackageSnapshot:
        """Raises `ValueError` when `source` is not a readable AASX package."""
        ...
