from excel_to_aasx.domain.compare import compare_snapshots, find_mount
from excel_to_aasx.domain.report import ComparisonReport, Mount
from excel_to_aasx.ports.package_reader import PackageReader


def compare_packages(
    reader: PackageReader, expected: str, reference: str, mount: Mount | None = None
) -> ComparisonReport:
    """Check that `reference` contains everything in `expected` (ADR 0003).

    Without `mount`, the submodel and container in `reference` that line up best are used.
    """
    produced = reader.read(expected)
    known = reader.read(reference)
    if mount is None:
        elements = next(iter(produced.submodels.values()), {})
        mount = find_mount(elements, known.submodels)
    if mount is None:
        raise ValueError("no element of the expected package occurs in the reference package")
    return compare_snapshots(produced, known, mount)
