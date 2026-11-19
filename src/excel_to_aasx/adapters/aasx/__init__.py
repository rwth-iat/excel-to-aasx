from excel_to_aasx.adapters.aasx.package import load_environment
from excel_to_aasx.adapters.aasx.snapshot import snapshot_of
from excel_to_aasx.adapters.aasx.writer import AasxPackageWriter
from excel_to_aasx.domain.snapshot import PackageSnapshot

__all__ = ["AasxPackageReader", "AasxPackageWriter"]


class AasxPackageReader:
    def __init__(self, max_part_bytes: int) -> None:
        self._max_part_bytes = max_part_bytes

    def read(self, source: str) -> PackageSnapshot:
        return snapshot_of(load_environment(source, self._max_part_bytes))
