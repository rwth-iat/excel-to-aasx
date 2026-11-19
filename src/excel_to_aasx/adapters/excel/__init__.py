"""Read a workbook as sheets of cell texts.

An .xlsx is an untrusted ZIP: the declared uncompressed size is checked before openpyxl
opens it. openpyxl parses its XML through defusedxml when that is installed (it is).
"""

import datetime
import zipfile
from collections.abc import Iterator

import openpyxl

from excel_to_aasx.domain.importing.model import Sheet


class ExcelSheetReader:
    def __init__(self, max_uncompressed_bytes: int) -> None:
        self._max_uncompressed_bytes = max_uncompressed_bytes

    def read(self, source: str) -> list[Sheet]:
        self._check_size(source)
        try:
            workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
        except (OSError, zipfile.BadZipFile, KeyError) as error:
            raise ValueError(f"{source}: not a readable .xlsx workbook ({error})") from error
        try:
            return [Sheet(ws.title, list(_rows(ws))) for ws in workbook.worksheets]
        finally:
            workbook.close()

    def _check_size(self, source: str) -> None:
        try:
            with zipfile.ZipFile(source) as package:
                total = sum(info.file_size for info in package.infolist())
        except (OSError, zipfile.BadZipFile) as error:
            raise ValueError(f"{source}: not a readable .xlsx workbook ({error})") from error
        if total > self._max_uncompressed_bytes:
            raise ValueError(
                f"{source}: unpacks to {total} bytes, limit {self._max_uncompressed_bytes}"
            )


def _rows(worksheet) -> Iterator[list[str]]:
    for row in worksheet.iter_rows(values_only=True):
        yield [cell_text(value) for value in row]


def cell_text(value: object) -> str:
    """Cell value as text, close to ClosedXML's `Value.ToString()` (spec 1.3)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    return str(value)
