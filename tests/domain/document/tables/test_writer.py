from excel_to_aasx.domain.document.tables.model import Element, Ref
from excel_to_aasx.domain.document.tables.preset import SMT_ASCIIDOC_PRESET
from excel_to_aasx.domain.document.tables.writer import TableRequest, write_table

SEM = Ref((("GlobalReference", "urn:general"),))


def _general(*children: Element) -> Element:
    return Element("SubmodelElementCollection", "General", semantic_id=SEM, children=children)


def _table(container: Element, **kwargs) -> str:
    request = TableRequest(
        container, Element("Submodel", "SM"), "Table_General", "Table for General", **kwargs
    )
    return "\n".join(write_table(SMT_ASCIIDOC_PRESET, request))


def test_table_header_and_top_rows():
    text = _table(_general(Element("Property", "Name", value_type="xs:string")))
    assert (
        '[width="100%", id="Table_General", title="Table for General", cols="15%,55%,15%,15%"]'
        in text
    )
    assert (
        "s|{set:cellbgcolor:#0029cc} [white]#idShort:#\n3+s|{set:cellbgcolor:#eeeeee}General \n"
        in text
    )
    assert "3+|{set:cellbgcolor:#eeeeee}SubmodelElementCollection \n" in text
    assert "3+|{set:cellbgcolor:#eeeeee}SM \n" in text  # Parent
    assert text.rstrip("\n").endswith("|===")


def test_body_row_per_child():
    text = _table(
        _general(Element("Property", "Name", value_type="xs:string", value_text="KROHNE"))
    )
    assert "|{set:cellbgcolor:#eeeeee}[Prop]  +\n +\nName\n" in text
    assert "|[xs:string]  +\n +\nKROHNE\n" in text


def test_column_widths_override():
    text = _table(_general(Element("Property", "Name")), column_widths=(10.0, 50.0, 30.0, 10.0))
    assert 'cols="10%,50%,30%,10%"' in text


def test_pipes_in_values_are_escaped():
    text = _table(_general(Element("Property", "Name", value_text="a|b")))
    assert "a\\|b" in text


def test_empty_container_writes_nothing():
    assert write_table(SMT_ASCIIDOC_PRESET, TableRequest(_general(), None, "T", "")) == [""]


def test_no_title_or_id_when_missing():
    request = TableRequest(_general(Element("Property", "Name")), None, "", "")
    assert '[width="100%", cols="15%,55%,15%,15%"]' in write_table(SMT_ASCIIDOC_PRESET, request)
