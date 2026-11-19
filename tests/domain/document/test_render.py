import json

from excel_to_aasx.domain.document.nodes import FUNCTION_PREFIX, DocNode, DocSource
from excel_to_aasx.domain.document.render import render_document

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def _blob(function, text, id_short="B"):
    return DocNode("Blob", id_short, function, content=text.encode(), content_type="text/markdown")


def _render(*nodes, name="Doc"):
    return render_document(DocSource(name, tuple(nodes)))


def test_headings_and_text_blocks_in_order():
    doc = _render(
        _blob("coverpage", "= Title"),
        DocNode(
            "SubmodelElementCollection",
            "S",
            children=(_blob("heading1", "Intro"), _blob("textblock", "Body")),
        ),
        _blob("heading2", "Sub"),
        _blob("textblock", ""),
    )
    assert doc.file_name == "Doc.adoc"
    assert doc.text == "= Title\n\n== Intro\nBody\n\n=== Sub\n"


def test_image_blob_is_written_and_linked_with_title_and_width():
    image = DocNode(
        "Blob", "Logo", "imagefile", title='The "logo"', args='{"width": 50}',
        content=PNG, content_type="image/png",
    )  # fmt: skip
    doc = _render(image)
    assert doc.assets == {"Logo.png": PNG}
    assert 'image::Logo.png[id="Logo", width="50.0%",title="The \\"logo\\""]' in doc.text


def test_no_link_and_file_name_args():
    theme = DocNode(
        "Blob", "theme_dot_yml", "imagefile", args='{"noLink": "true"}',
        content=b"x: 1", content_type="text/plain",
    )  # fmt: skip
    font = DocNode(
        "File", "Font", "imagefile", args='{"noLink": true, "fileName": "../F.ttf"}',
        content=b"ttf", file_path="/aasx/files/F.ttf",
    )  # fmt: skip
    doc = _render(theme, font)
    assert doc.assets == {"theme.yml": b"x: 1", "F.ttf": b"ttf"}
    assert "image::" not in doc.text
    assert [i.message for i in doc.issues] == ["fileName '../F.ttf' changed to 'F.ttf'"]


def test_missing_image_data_is_an_error():
    doc = _render(DocNode("File", "Gone", "imagefile", file_path="http://x/y.png"))
    assert [i.severity for i in doc.issues] == ["error"]


def test_iterate_list_repeats_children_with_items():
    args = json.dumps({"itemsA": ["One", "Two"], "itemsB": ["first"], "itemsC": ["c1", "c2"]})
    loop = DocNode(
        "SubmodelElementCollection", "Loop", "iterate-list", args=args,
        children=(
            _blob("heading2", "%ITEMA% (%ITEMB%)"),
            DocNode(
                "ReferenceElement", "Table_%ITEMA%", "generate-tables", reference=("sm", "%ITEMA%")
            ),
            _blob("textblock", "%ITEMC%"),
        ),
    )  # fmt: skip
    doc = _render(loop)
    assert doc.text == (
        "\n=== One (first)\n\n// table 'Table_One' from sm/One: not generated yet\n\nc1\n"
        "\n=== Two ()\n\n// table 'Table_Two' from sm/Two: not generated yet\n\nc2\n"
    )


def test_iterate_list_without_items_is_an_error():
    loop = DocNode(
        "SubmodelElementCollection", "Loop", "iterate-list", children=(_blob("textblock", "x"),)
    )
    doc = _render(loop)
    assert doc.text == "\n" and [i.severity for i in doc.issues] == ["error"]


def test_generated_parts_are_marked_until_implemented():
    doc = _render(DocNode("ReferenceElement", "UML_X", "generate-uml", reference=("sm", "X")))
    assert "// UML diagram 'UML_X' from sm/X: not generated yet" in doc.text
    assert [i.severity for i in doc.issues] == ["warning"]


def test_prefix_constant_matches_package_explorer():
    assert FUNCTION_PREFIX == "http://admin-shell.io/aasx-package-explorer/functions/asciidoc/"
