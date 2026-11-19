import datetime
import json

from excel_to_aasx.domain.document.starter import Frame, starter_nodes
from excel_to_aasx.domain.document.tables.model import Element

TODAY = datetime.date(2026, 11, 19)
FRAME = Frame(
    {
        "cover": "= {{number}} : {{title}}\n{{month}}",
        "front": "v {{date}} {{unknown}}",
        "back": "B",
    },
    {"my-theme.yml": b"x: 1", "logo.png": b"\x89PNG"},
)


def _data() -> Element:
    item = Element("SubmodelElementCollection", "", children=(Element("File", "ImageFile"),))
    images = Element("SubmodelElementList", "ProductImages", children=(item,))
    general = Element(
        "SubmodelElementCollection", "General", children=(Element("Property", "Name"), images)
    )
    empty = Element("SubmodelElementCollection", "Empty")
    return Element("Submodel", "My{Model}", children=(general, empty))


def _flat(nodes):
    for node in nodes:
        yield node
        yield from _flat(node.children)


def test_frame_parts_are_filled():
    nodes = {n.id_short: n for n in starter_nodes(_data(), "urn:sm", FRAME, TODAY)}
    assert nodes["CoverPage"].function == "coverpage"
    assert nodes["CoverPage"].content == b"= [IDTA number] : My\\{Model}\nNovember 2026"
    assert nodes["Front_matter"].content == b"v 2026-11-19 {{unknown}}"
    assert nodes["Back_matter"].content == b"B"


def test_assets_become_unlinked_image_files():
    fixed = starter_nodes(_data(), "urn:sm", FRAME, TODAY)[0]
    by_id = {n.id_short: n for n in fixed.children}
    assert set(by_id) == {"my-theme_dot_yml", "logo_dot_png"}
    assert by_id["my-theme_dot_yml"].content_type == "text/plain"
    assert json.loads(by_id["logo_dot_png"].args) == {"noLink": True}


def test_generated_chapter_has_uml_and_a_table_per_container():
    refs = [
        n
        for n in _flat(starter_nodes(_data(), "urn:sm", FRAME, TODAY))
        if n.kind == "ReferenceElement"
    ]
    assert [(n.id_short, n.reference) for n in refs] == [
        ("UML_Submodel", ("urn:sm",)),
        ("Table_Submodel", ("urn:sm",)),
        ("Table_General", ("urn:sm", "General")),
        ("Table_General_ProductImages", ("urn:sm", "General", "ProductImages")),
        ("Table_General_ProductImages_0", ("urn:sm", "General", "ProductImages", "0")),
    ]
    assert refs[4].title == "Table for SMC ProductImages[0]"
    assert json.loads(refs[0].args)["depth"] == 2
