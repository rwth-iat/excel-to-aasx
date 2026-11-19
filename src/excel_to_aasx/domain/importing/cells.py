"""How single cells are read. Each rule cites the C# it reproduces (spec sections 4-5)."""

import re

from excel_to_aasx.domain.importing.model import LangText

DEFAULT_LANGUAGE = "en"

# AasSubmodelElementsFromStringOrAbbrev: full name or abbreviation, case-sensitive.
_ABBREVIATIONS = {
    "RelA": "AnnotatedRelationshipElement",
    "BEvt": "BasicEventElement",
    "Blob": "Blob",
    "Cap": "Capability",
    "Ent": "Entity",
    "File": "File",
    "MLP": "MultiLanguageProperty",
    "Opr": "Operation",
    "Prop": "Property",
    "Range": "Range",
    "Ref": "ReferenceElement",
    "Rel": "RelationshipElement",
    "SML": "SubmodelElementList",
    "SMC": "SubmodelElementCollection",
}
_ELEMENT_KINDS = frozenset(_ABBREVIATIONS.values())
# Enum AasSubmodelElements, including its abstract members; compared case-insensitively.
_ENUM_NAMES_LOWER = frozenset(
    name.lower() for name in (*_ELEMENT_KINDS, "SubmodelElement", "DataElement", "EventElement")
)

XSD_TYPES = frozenset(
    f"xs:{name}"
    for name in [
        "anyURI",
        "base64Binary",
        "boolean",
        "byte",
        "date",
        "dateTime",
        "decimal",
        "double",
        "duration",
        "float",
        "gDay",
        "gMonth",
        "gMonthDay",
        "gYear",
        "gYearMonth",
        "hexBinary",
        "int",
        "integer",
        "long",
        "negativeInteger",
        "nonNegativeInteger",
        "nonPositiveInteger",
        "positiveInteger",
        "short",
        "string",
        "time",
        "unsignedByte",
        "unsignedInt",
        "unsignedLong",
        "unsignedShort",
    ]
)
_XSD_BY_LOWER = {name.lower(): name for name in XSD_TYPES}

_CARDINALITY = {
    "0..1": "ZeroToOne", "[0..1]": "ZeroToOne", "ZeroToOne": "ZeroToOne",
    "0..*": "ZeroToMany", "[0..*]": "ZeroToMany", "ZeroToMany": "ZeroToMany",
    "1..*": "OneToMany", "[1..*]": "OneToMany", "OneToMany": "OneToMany",
}  # fmt: skip

_ID_SHORT = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9_]+$")


def parse_element_kind(text: str) -> str | None:
    """FilteredElementName.Parse: `SMC`, `[SMC]`, `SMC / x`; "Submodel" for a submodel."""
    name = text.strip()
    if not name:
        return None
    for pattern in (r"\[\s*(\w+)\s*\]\s*/\s*(\w+)", r"(\w+)\s*/\s*(\w+)", r"\[\s*(\w+)\s*\]"):
        if found := re.search(pattern, name):
            name = found.group(1)
            break
    if name.lower() == "submodel":
        return "Submodel"
    if name in _ELEMENT_KINDS:
        return name
    return _ABBREVIATIONS.get(name)


def parse_value_type(text: str) -> tuple[str, str | None]:
    """Returns (value type, suspected intended type). `""` means: leave the default.

    PE takes the text as is; anything it cannot parse is xs:string. The second value
    names the type a near miss like `xs: date` or `xs:Boolean` probably meant.
    """
    value = text
    if bracketed := re.match(r"^\s*\[(.*)\]", value):
        value = bracketed.group(1)
    stripped = value.strip()
    if stripped == "n/a" or stripped.lower() in _ENUM_NAMES_LOWER:
        return "", None
    if value in XSD_TYPES:
        return value, None
    if not stripped:
        return "xs:string", None
    return "xs:string", _XSD_BY_LOWER.get(re.sub(r"\s+", "", stripped).lower())


def parse_cardinality(text: str) -> str:
    return _CARDINALITY.get(text.strip(), "One")


def parse_lang_strings(text: str) -> list[LangText]:
    """ExtendLangStringSet.Parse: `text@en text@de`; text without `@` is the default language."""
    result: list[LangText] = []
    rest = text
    while "@" in rest:
        found = re.search(r"(.*?)@(\w+)", rest, re.DOTALL)
        if not found:
            break
        result.append((found.group(2), found.group(1).strip()))
        rest = rest[found.end() :]
    if rest.strip():
        result.append((DEFAULT_LANGUAGE, rest))
    return result


def is_valid_id_short(text: str) -> bool:
    return bool(_ID_SHORT.match(text))
