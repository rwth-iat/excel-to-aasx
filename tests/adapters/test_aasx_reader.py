import zipfile
from pathlib import Path

import pytest

from excel_to_aasx.adapters.aasx import AasxPackageReader
from tests.aasx_fixture import collection, environment, property_, submodel, write_aasx

EXAMPLE = (
    Path(__file__).parents[2]
    / "examples"
    / ("Namur_SMT_VariableAreaFlowMeters_v09_2nd_delivery (1).aasx")
)
LIMIT = 10 * 1024 * 1024


def test_reads_example_package():
    snapshot = AasxPackageReader(LIMIT).read(str(EXAMPLE))

    data = snapshot.submodels["NamurTechnicalDataVariableAreaFlowMeter"]
    number = data["TechnicalPropertyAreas/ECLASS_ADV_V17/General/ManufacturerArticleNumber"]
    assert (number.kind, number.cardinality, number.value_type) == ("Property", "One", "xs:string")
    assert len(snapshot.concepts) == 99


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
