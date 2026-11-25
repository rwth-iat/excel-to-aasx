"""The invented demo workbook (tools/make_demo_workbook.py): the only workbook tests read.

Tests never depend on third-party reference files (ADR 0010).
"""

from pathlib import Path

DEMO = Path(__file__).parents[1] / "src/excel_to_aasx/adapters/web/static/examples/demo-level-sensor.xlsx"
LIMIT = 10 * 1024 * 1024
