import io
from functools import partial

from excel_to_aasx.adapters import cli
from excel_to_aasx.adapters.aasx import AasxPackageReader
from excel_to_aasx.app.compare_packages import compare_packages
from tests.aasx_fixture import collection, environment, property_, submodel, write_aasx
from tests.adapters.test_aasx_reader import LIMIT

NAMES = {"en": "manufacturer article number", "de": "Herstellerartikelnummer"}


def _diff(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    compare = partial(compare_packages, AasxPackageReader(LIMIT))
    return cli.run(
        ["diff", *args],
        compare=compare,
        import_=_no_import,
        export=_no_import,
        pdf=_no_import,
        add_document=_no_import,
        out=out,
    ), out.getvalue()


def _general(*children):
    names = {"en": "General", "de": "Allgemein"}
    return collection("General", "s:general", *children, names=names)


def _reference(tmp_path) -> str:
    """Imported tree below a mount point, plus later edits: the shape ADR 0003 describes."""
    edited = environment(
        submodel(
            "TechnicalData",
            collection(
                "TechnicalPropertyAreas",
                "s:areas",
                collection(
                    "Imported",
                    "s:imported",
                    _general(
                        property_("ArticleNumber", "s:article", names=NAMES),
                        property_("AddedLater", "s:added"),
                    ),
                ),
            ),
        )
    )
    return str(write_aasx(tmp_path / "reference.aasx", edited))


def test_subset_of_reference_has_no_differences(tmp_path):
    produced = environment(
        submodel("Import", _general(property_("ArticleNumber", "s:article", names=NAMES)))
    )
    code, out = _diff(str(write_aasx(tmp_path / "p.aasx", produced)), _reference(tmp_path))
    assert code == 0, out
    assert "TechnicalData/TechnicalPropertyAreas/Imported" in out


def test_reports_differences_against_reference(tmp_path):
    produced = environment(
        submodel(
            "Import",
            _general(
                property_("ArticleNumber", "s:article", "ZeroToOne", NAMES),
                property_("NotInReference", "x:y"),
            ),
        )
    )
    code, out = _diff(str(write_aasx(tmp_path / "p.aasx", produced)), _reference(tmp_path))
    assert code == 1
    assert "General/ArticleNumber  cardinality: 'ZeroToOne' != 'One'" in out
    assert "General/NotInReference  missing" in out


def test_explicit_mount_and_bad_input(tmp_path):
    produced = environment(submodel("Import", _general()))
    path = str(write_aasx(tmp_path / "p.aasx", produced))
    code, out = _diff(path, _reference(tmp_path), "--submodel", "TechnicalData")
    assert code == 1 and "General  missing" in out
    assert _diff(path, str(tmp_path / "missing.aasx"))[0] == 2


def _no_import(*_args):
    raise AssertionError("import not expected")
