import zipfile
import pytest

from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.app.import_workbook import import_workbook
from tests.aasx_fixture import collection, environment, property_, submodel, write_aasx
from tests.demo import DEMO

LIMIT = 10 * 1024 * 1024


def test_reads_imported_demo_package(tmp_path):
    package = tmp_path / "demo.aasx"
    import_workbook(ExcelSheetReader(LIMIT), AasxPackageWriter(), str(DEMO), str(package))
    snapshot = AasxPackageReader(LIMIT).read(str(package))

    data = snapshot.submodels["DemoLevelSensor"]
    name = data["General/ManufacturerName"]
    assert (name.kind, name.cardinality, name.value_type) == ("Property", "One", "xs:string")
    assert data["MeasuringRange/ProcessTemperature"].kind == "Range"
    assert len(snapshot.concepts) == 17


def test_paths_follow_nesting(tmp_path):
    env = environment(submodel("S", collection("A", "s:a", property_("B", "s:b", "ZeroToOne"))))
    snapshot = AasxPackageReader(LIMIT).read(str(write_aasx(tmp_path / "t.aasx", env)))
    assert list(snapshot.submodels["S"]) == ["A", "A/B"]
    assert snapshot.submodels["S"]["A/B"].cardinality == "ZeroToOne"


def test_rejects_oversized_part(tmp_path):
    path = write_aasx(tmp_path / "t.aasx", environment(submodel("S")))
    with pytest.raises(ValueError, match="limit 100"):
        AasxPackageReader(100).read(str(path))


def test_rejects_non_zip(tmp_path):
    path = tmp_path / "t.aasx"
    path.write_text("not a zip")
    with pytest.raises(ValueError, match="not a ZIP"):
        AasxPackageReader(LIMIT).read(str(path))


def test_rejects_package_without_origin(tmp_path):
    path = tmp_path / "t.aasx"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
    with pytest.raises(ValueError, match="aasx-origin"):
        AasxPackageReader(LIMIT).read(str(path))


def test_rejects_xml_entities(tmp_path):
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE e [<!ENTITY a "aaaa">]>'
        '<environment xmlns="https://admin-shell.io/aas/3/1">&a;</environment>'
    )
    path = write_aasx(tmp_path / "t.aasx", environment(), spec_xml=bomb)
    with pytest.raises(ValueError, match="forbidden XML"):
        AasxPackageReader(LIMIT).read(str(path))
