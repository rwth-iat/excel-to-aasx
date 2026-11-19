from excel_to_aasx.domain.importing.blocks import Block, BodyRow, Top
from excel_to_aasx.domain.importing.build import build_submodel, generated_id
from excel_to_aasx.domain.importing.model import SubmodelDraft


def _top(id_short, element_name, parent="", semantic_id="", explanation=""):
    return Top("S!1", id_short, element_name, semantic_id, parent, explanation)


def _row(id_short, kind="Prop", semantic_id=None, value_type="xs:string", **cells):
    values = {
        "display_name_en": "", "display_name_de": "", "cd_id_short": "",
        "preferred_name_en": "", "preferred_name_de": "", "definition_en": "",
        "definition_de": "", "unit": "", "multiplicity": "One",
    } | cells  # fmt: skip
    sid = f"urn:{id_short}" if semantic_id is None else semantic_id
    return BodyRow("S!7", id_short, sid, element_name=kind, value_type=value_type, **values)


def _build(*blocks):
    return build_submodel(list(blocks), SubmodelDraft(id="urn:sm", id_short=""))


ROOT = Block(
    _top("SM", "Submodel", semantic_id="urn:sm-sem", explanation="About@en Über@de"),
    (_row("General", "SMC"), _row("Name", "MLP", display_name_en="name", multiplicity="ZeroToOne")),
)


def test_submodel_block_takes_over_top_and_fills_root():
    result = _build(ROOT)
    sm = result.submodel
    assert (sm.id_short, sm.semantic_id, sm.description) == (
        "SM", "urn:sm-sem", [("en", "About"), ("de", "Über")]
    )  # fmt: skip
    assert [(e.kind, e.id_short) for e in sm.elements] == [
        ("SubmodelElementCollection", "General"),
        ("MultiLanguageProperty", "Name"),
    ]
    name = sm.elements[1]
    assert (name.cardinality, name.display_names, name.value_type) == (
        "ZeroToOne",
        [("en", "name")],
        "",
    )


def test_collection_block_continues_existing_collection_and_drops_its_top_data():
    child = Block(
        _top("General", "SubmodelElementCollection", parent="SM", explanation="dropped"),
        (_row("Number", value_type="xs:int"),),
    )
    general = _build(ROOT, child).submodel.elements[0]
    assert [(e.id_short, e.value_type) for e in general.children] == [("Number", "xs:int")]
    assert general.description == []


def test_collection_block_alias_resolves_grandchildren():
    child = Block(_top("General", "SMC", parent="SM"), (_row("Inner", "SMC"),))
    grandchild = Block(_top("Inner", "SMC", parent="General"), (_row("Deep"),))
    sm = _build(ROOT, child, grandchild).submodel
    assert sm.elements[0].children[0].children[0].id_short == "Deep"


def test_unmatched_collection_block_becomes_new_root_collection():
    block = Block(_top("Other", "SMC", parent="Nowhere", semantic_id="urn:o"), (_row("X"),))
    sm = _build(ROOT, block).submodel
    assert [e.id_short for e in sm.elements] == ["General", "Name", "Other"]
    assert sm.elements[2].semantic_id == "urn:o"


def test_concepts_first_row_wins_and_empty_texts_are_skipped():
    block = Block(
        _top("SM", "Submodel"),
        (
            _row("A", semantic_id="urn:x", cd_id_short="CdA", preferred_name_en="a", unit="mm"),
            _row("B", semantic_id="urn:x", cd_id_short="CdB", preferred_name_en="b"),
            _row("C", semantic_id="urn:c"),
        ),
    )
    concepts = _build(block).concepts
    assert [(c.id, c.id_short, c.preferred_names, c.unit) for c in concepts] == [
        ("urn:x", "CdA", (("en", "a"),), "mm"),
        ("urn:c", "C", (), ""),
    ]


def test_row_without_semantic_id_gets_stable_generated_id():
    block = Block(_top("SM", "Submodel"), (_row("A", semantic_id=""),))
    first, second = _build(block), _build(block)
    generated = first.submodel.elements[0].semantic_id
    assert generated.startswith("www.example.com/ids/cd/") and "D" not in generated
    assert generated == second.submodel.elements[0].semantic_id == first.concepts[0].id


def test_errors_skip_row_without_creating_concept():
    block = Block(_top("SM", "Submodel"), (_row("Aa", "Foo"), _row("Bb"), _row("Bb")))
    result = _build(block)
    assert [e.id_short for e in result.submodel.elements] == ["Bb"]
    assert [c.id for c in result.concepts] == ["urn:Bb"]
    assert [i.severity for i in result.issues] == ["error", "error"]
    assert result.has_errors


def test_warnings_for_near_miss_value_type_and_invalid_id_short():
    block = Block(_top("SM", "Submodel"), (_row("pressure drop", value_type="xs:Boolean"),))
    result = _build(block)
    assert result.submodel.elements[0].value_type == "xs:string"
    assert [i.severity for i in result.issues] == ["warning", "warning", "warning"]
    assert not result.has_errors


def test_unknown_class_skips_block():
    result = _build(Block(_top("X", "Property"), (_row("A"),)))
    assert result.submodel.elements == [] and result.has_errors


def test_generated_id_fills_template():
    assert generated_id("x/DD_DD", "seed") == generated_id("x/DD_DD", "seed")
    assert generated_id("x/DD_DD", "seed") != generated_id("x/DD_DD", "other")
