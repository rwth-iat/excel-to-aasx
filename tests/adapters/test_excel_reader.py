import datetime

import openpyxl
import pytest

from excel_to_aasx.adapters.excel import ExcelSheetReader, cell_text
from tests.adapters.test_aasx_reader import EXAMPLE

WORKBOOK = EXAMPLE.with_name("Import_Properties_Schwebe_2_added_Li_v09_HOMI_Gerd-1.xlsx")
LIMIT = 50 * 1024 * 1024


def test_reads_all_sheets_of_example():
    sheets = ExcelSheetReader(LIMIT).read(str(WORKBOOK))
    assert [s.name for s in sheets] == ["Import", "README"]
    assert sheets[0].rows[0][:2] == ["idShort:", "NAMUR_SMT_FloatTypeFowMeter"]


@pytest.mark.parametrize(
    ("value", "text"),
    [(None, ""), ("x", "x"), (3, "3"), (3.0, "3"), (2.5, "2.5"), (True, "True"),
     (datetime.date(2026, 1, 2), "2026-01-02")],
)  # fmt: skip
def test_cell_text(value, text):
    assert cell_text(value) == text


def test_rejects_workbook_over_size_limit():
    with pytest.raises(ValueError, match="limit 1000"):
        ExcelSheetReader(1000).read(str(WORKBOOK))


def test_rejects_non_workbook(tmp_path):
    path = tmp_path / "x.xlsx"
    path.write_text("nope")
    with pytest.raises(ValueError, match="not a readable"):
        ExcelSheetReader(LIMIT).read(str(path))


def test_formulas_give_cached_value(tmp_path):
    book = openpyxl.Workbook()
    sheet = book.create_sheet("F", 0)
    sheet.append(["=1+1"])
    book.save(tmp_path / "f.xlsx")
    rows = ExcelSheetReader(LIMIT).read(str(tmp_path / "f.xlsx"))[0].rows
    assert rows == [[""]]  # never calculated by Excel, so no cached value exists
