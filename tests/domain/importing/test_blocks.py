from excel_to_aasx.domain.importing.blocks import find_blocks

TOP = [["idShort:", "SM"], ["Class:", "Submodel"], ["semanticId:", "urn:sm"],
       ["Parent:", ""], ["Explanation:", "text"], ["SME.idShort", "SME.semanticId"]]  # fmt: skip


def _row(id_short: str) -> list[str]:
    return [id_short, f"urn:{id_short}"] + [""] * 8 + ["Prop", "xs:string", "One"]


def test_finds_blocks_separated_by_empty_rows():
    rows = [*TOP, _row("A"), _row("B"), [], [], [], *TOP, _row("C")]
    blocks = find_blocks("S", rows)
    assert [len(b.body) for b in blocks] == [2, 1]
    assert blocks[0].top.location == "S!1"
    assert blocks[0].body[1].location == "S!8"
    assert (blocks[0].top.id_short, blocks[0].top.element_name) == ("SM", "Submodel")
    assert blocks[0].body[0].element_name == "Prop"


def test_body_ends_at_first_empty_row():
    blocks = find_blocks("S", [*TOP, _row("A"), [], _row("orphan")])
    assert [r.sme_id_short for r in blocks[0].body] == ["A"]


def test_skips_noise_and_ignores_extra_columns():
    rows = [["notes"], *TOP, [*_row("A"), "extra column N"]]
    blocks = find_blocks("S", rows)
    assert len(blocks) == 1 and blocks[0].body[0].multiplicity == "One"


def test_top_labels_must_match_exactly():
    rows = [["idshort:", "SM"], *TOP[1:], _row("A")]
    assert find_blocks("S", rows) == []


def test_stops_after_100_empty_rows():
    assert find_blocks("S", [[]] * 100 + [*TOP, _row("A")]) == []
    assert len(find_blocks("S", [[]] * 99 + [*TOP, _row("A")])) == 1
