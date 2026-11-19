"""Composition root: the only place that constructs adapters."""

import sys
from functools import partial

from excel_to_aasx.adapters import cli
from excel_to_aasx.adapters.aasx import AasxPackageReader
from excel_to_aasx.app.compare_packages import compare_packages

MAX_PACKAGE_PART_BYTES = 200 * 1024 * 1024


def main() -> int:
    reader = AasxPackageReader(max_part_bytes=MAX_PACKAGE_PART_BYTES)
    return cli.run(sys.argv[1:], compare=partial(compare_packages, reader))


if __name__ == "__main__":
    sys.exit(main())
