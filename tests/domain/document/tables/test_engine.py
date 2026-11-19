import pytest

from excel_to_aasx.domain.document.tables.cells import CellFiller
from excel_to_aasx.domain.document.tables.model import Concept, Element, Ref, resolve
from excel_to_aasx.domain.document.tables.placeholders import Placeholders, placeholders_for
from excel_to_aasx.domain.document.tables.preset import SMT_ASCIIDOC_PRESET, TablePreset
from excel_to_aasx.domain.ids import remove_version

SEM = Ref((("GlobalReference", "0173-1#02-AAO677#004"),))
SUPPL = (Ref((("GlobalReference", "https://api.eclass-cdp.com/x"),)),)


def _ph(**values: str) -> Placeholders:
    ph = Placeholders()
    for tag, value in values.items():
        ph.set(tag, value)
    return ph


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("0173-1#02-AAO677#004", "0173-1#02-AAO677"),
        ("0173-1#02-ABK161#002/0173-1#01-AHX838#002", "0173-1#02-ABK161/0173-1#01-AHX838"),
        ("http://admin-shell.io/aas/1/0", "http://admin-shell.io/aas"),
        ("https://namur.net/aas/x/1/0", "https://namur.net/aas/x/1/0"),
        ("0173-1#02-AAO677", "0173-1#02-AAO677"),
    ],
)
def test_remove_version_matches_package_explorer(identifier, expected):
    assert remove_version(identifier) == expected


def test_builtin_preset_shape():
    preset = SMT_ASCIIDOC_PRESET
    assert (preset.rows_top, preset.rows_body, preset.cols) == (7, 1, 4)
    assert len(preset.top) == 8 * 5 and len(preset.body) == 2 * 5
    text, with_headers = preset.top_cell(0, 1)
    assert text == "%Parent.idShort% %colspan=3%"
    assert with_headers.startswith(
        "%frame=2% %table-bg=#eeeeee% %md=headline% %font=bold% %width=55%"
    )


def test_preset_from_record_rejects_incomplete():
    with pytest.raises(ValueError, match="incomplete"):
        TablePreset.from_record({"Cols": 2})


def test_fill_replaces_counts_and_fails():
    filler = CellFiller(_ph(**{"sme.idshort": "Name"}), fail_text="")
    cell = filler.fill("[%SME.idShort%] %Unknown%", "", 0)
    assert cell.text == "[Name] "
    assert filler.replacements == 1


def test_fill_keeps_unknown_when_not_replacing_failed():
    cell = CellFiller(_ph(), fail_text=None).fill("%Unknown%", "", 0)
    assert cell.text == "%Unknown%"


def test_fill_reads_commands_from_headers_and_removes_them():
    filler = CellFiller(_ph(), fail_text="", column_widths=(20.0, 30.0))
    cell = filler.fill(
        "idShort: %bg=#0029cc% %fg=white%",
        "%font=bold% %width=15% idShort: %bg=#0029cc% %fg=white%",
        1,
    )
    assert (cell.bg, cell.fg, cell.font, cell.width) == ("#0029cc", "white", "bold", 30.0)
    assert cell.text.strip() == "idShort:"


def test_fill_colspan_trim_stop_and_newlines():
    filler = CellFiller(_ph(a="x\r\ny"), fail_text="")
    cell = filler.fill("  %a%  %colspan=3% %trim=all%", "%colspan=3% %trim=all%", 0)
    assert cell.col_span == 3
    assert cell.text == "x +\r\ny"
    assert CellFiller(_ph(), fail_text="").fill("left %stop% right", "", 0).text == "left"


def test_advanced_label_replacement():
    item = Element("Property", "P", semantic_id=SEM, supplemental_ids=SUPPL)
    ph = placeholders_for(item, 1, Element("Submodel", "S"), None)
    cell = CellFiller(ph, fail_text="").fill("%SME.supplSemIds[label=SSI]%", "", 0)
    assert cell.text == "SSI: https://api.eclass-cdp.com/x"


def test_placeholders_for_property_row():
    concept = Concept(definitions=(("de", "Def"), ("en", "definition")), unit="mm")
    item = Element(
        "Property", "Length", semantic_id=SEM, qualifiers=(("SMT/Cardinality", "ZeroToOne"),),
        value_text="12", value_type="xs:double", concept=concept,
    )  # fmt: skip
    parent = Element("SubmodelElementCollection", "General", description=(("en", "About"),))
    values = placeholders_for(item, 1, parent, Element("Submodel", "SM")).values
    assert values["sme.elementshort"] == "Prop"
    assert values["sme.multiplicity"] == "0..1"
    assert values["sme.packvalue[fmt=4]"] == "[xs:double]\r\n%BRPOST%12\r\n%BRPOST%(mm)"
    assert values["sme.packdescription[fmt=2]"] == "definition"
    assert values["sme.packsemids[fmt=4]"] == "0173-1#02-AAO677#004 \r\n%BRPOST%"
    assert values["parent.parent"] == "SM"
    assert values["parent.description@en"] == "About"


def test_resolve_follows_ids_and_list_indexes():
    leaf = Element("Property", "Leaf")
    item = Element("SubmodelElementCollection", "", children=(leaf,))
    sml = Element("SubmodelElementList", "Items", children=(item,))
    models = {"urn:sm": Element("Submodel", "SM", children=(sml,))}
    located = resolve(models, ["urn:sm", "Items", "0", "Leaf"])
    assert located is not None and located.element is leaf and located.parent is item
    assert resolve(models, ["urn:sm", "Items", "1"]) is None
    assert resolve(models, ["urn:other"]) is None
