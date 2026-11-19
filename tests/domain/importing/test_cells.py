import pytest

from excel_to_aasx.domain.importing.cells import (
    XSD_TYPES,
    is_valid_id_short,
    parse_cardinality,
    parse_element_kind,
    parse_lang_strings,
    parse_value_type,
)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("SMC", "SubmodelElementCollection"),
        ("SubmodelElementCollection", "SubmodelElementCollection"),
        (" [MLP] ", "MultiLanguageProperty"),
        ("[Prop] / xs:string", "Property"),
        ("SML / x", "SubmodelElementList"),
        ("submodel", "Submodel"),
        ("smc", None),
        ("Foo", None),
        ("", None),
    ],
)
def test_parse_element_kind(text, kind):
    assert parse_element_kind(text) == kind


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("xs:float", ("xs:float", None)),
        ("[xs:int]", ("xs:int", None)),
        ("", ("xs:string", None)),
        ("xs:Boolean", ("xs:string", "xs:boolean")),
        ("xs: date", ("xs:string", "xs:date")),
        ("whatever", ("xs:string", None)),
        ("n/a", ("", None)),
        ("SubmodelElementCollection", ("", None)),
    ],
)
def test_parse_value_type(text, expected):
    assert parse_value_type(text) == expected


def test_xsd_types_match_aas_core():
    import aas_core3_1.types as aas

    assert {t.value for t in aas.DataTypeDefXSD} == XSD_TYPES


@pytest.mark.parametrize(
    ("text", "cardinality"),
    [("ZeroToOne", "ZeroToOne"), ("[0..*]", "ZeroToMany"), ("1..*", "OneToMany"),
     ("One", "One"), ("", "One"), ("optional", "One")],
)  # fmt: skip
def test_parse_cardinality(text, cardinality):
    assert parse_cardinality(text) == cardinality


def test_parse_lang_strings():
    assert parse_lang_strings("") == []
    assert parse_lang_strings("plain text") == [("en", "plain text")]
    assert parse_lang_strings("Hallo@de Hello@en") == [("de", "Hallo"), ("en", "Hello")]
    assert parse_lang_strings("Hallo@de-DE") == [("de-DE", "Hallo")]
    assert parse_lang_strings("Questions: support@krohne.com") == [
        ("en", "Questions: support@krohne.com")
    ]
    assert parse_lang_strings("Mail a@b.de@de Mail@en") == [("de", "Mail a@b.de"), ("en", "Mail")]
    assert parse_lang_strings("Hallo@de and more") == [("de", "Hallo"), ("en", "and more")]


def test_is_valid_id_short():
    assert is_valid_id_short("ManufacturerName")
    assert not is_valid_id_short("pressure drop")
    assert not is_valid_id_short("1abc")
