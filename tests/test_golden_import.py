"""Import the demo workbook end to end through the CLI."""

import io
import zipfile
from functools import partial

from excel_to_aasx.adapters import cli
from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.app.compare_packages import compare_packages
from excel_to_aasx.app.import_workbook import import_workbook
from tests.demo import DEMO, LIMIT


def _run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = cli.run(
        list(argv),
        compare=partial(compare_packages, AasxPackageReader(LIMIT)),
        import_=partial(import_workbook, ExcelSheetReader(LIMIT), AasxPackageWriter()),
        export=_unused,
        pdf=_unused,
        add_document=_unused,
        out=out,
    )
    return code, out.getvalue()


def test_demo_workbook_imports_and_diffs_cleanly(tmp_path):
    target = str(tmp_path / "import.aasx")
    code, out = _run("import", str(DEMO), "-o", target)
    assert code == 0, out
    assert "submodel DemoLevelSensor" in out
    assert "17 concepts; 0 error(s), 0 warning(s)" in out

    code, out = _run("diff", target, target)
    assert code == 0, out
    assert "checked 17 elements, 17 concepts: 0 difference(s)" in out


def test_import_is_deterministic(tmp_path):
    first, second = tmp_path / "a.aasx", tmp_path / "b.aasx"
    _run("import", str(DEMO), "-o", str(first))
    _run("import", str(DEMO), "-o", str(second))
    assert _spec_xml(first) == _spec_xml(second)


def test_output_has_only_known_metamodel_findings(tmp_path):
    _, out = _run("import", str(DEMO), "-o", str(tmp_path / "x.aasx"))
    findings = [line for line in out.splitlines() if "metamodel:" in line]
    assert findings == []


def _spec_xml(path) -> bytes:
    with zipfile.ZipFile(path) as package:
        return next(package.read(n) for n in package.namelist() if n.endswith(".aas.xml"))


def _unused(*_args):
    raise AssertionError("not expected")
