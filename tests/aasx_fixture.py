"""Build small AASX packages for tests."""

import zipfile
from pathlib import Path

import aas_core3_1.types as aas
import aas_core3_1.xmlization as aas_xml

SPEC_PART = "aasx/data.aas.xml"


def write_aasx(path: Path, environment: aas.Environment, spec_xml: str | None = None):
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    with zipfile.ZipFile(path, "w") as package:
        package.writestr(
            "_rels/.rels",
            f'{rels}<Relationship Type="http://admin-shell.io/aasx/relationships/aasx-origin" '
            'Target="/aasx/aasx-origin" Id="r1"/></Relationships>',
        )
        package.writestr("aasx/aasx-origin", "Intentionally empty.")
        package.writestr(
            "aasx/_rels/aasx-origin.rels",
            f'{rels}<Relationship Type="http://admin-shell.io/aasx/relationships/aas-spec" '
            f'Target="/{SPEC_PART}" Id="r2"/></Relationships>',
        )
        package.writestr(SPEC_PART, spec_xml or aas_xml.to_str(environment))
    return path


def _cardinality(value: str) -> aas.Qualifier:
    return aas.Qualifier(type="SMT/Cardinality", value_type=aas.DataTypeDefXSD.STRING, value=value)


def _global_ref(value: str) -> aas.Reference:
    return aas.Reference(
        type=aas.ReferenceTypes.EXTERNAL_REFERENCE,
        keys=[aas.Key(type=aas.KeyTypes.GLOBAL_REFERENCE, value=value)],
    )


def property_(
    id_short: str, semantic_id: str, card: str = "One", names: dict[str, str] | None = None
) -> aas.Property:
    return aas.Property(
        id_short=id_short,
        value_type=aas.DataTypeDefXSD.STRING,
        semantic_id=_global_ref(semantic_id),
        qualifiers=[_cardinality(card)],
        display_name=_names(names),
    )


def collection(
    id_short: str,
    semantic_id: str,
    *children: aas.SubmodelElement,
    names: dict[str, str] | None = None,
):
    return aas.SubmodelElementCollection(
        id_short=id_short,
        semantic_id=_global_ref(semantic_id),
        qualifiers=[_cardinality("One")],
        value=list(children),
        display_name=_names(names),
    )


def environment(*submodels: aas.Submodel) -> aas.Environment:
    return aas.Environment(submodels=list(submodels))


def submodel(id_short: str, *elements: aas.SubmodelElement) -> aas.Submodel:
    return aas.Submodel(
        id=f"urn:test:{id_short}", id_short=id_short, submodel_elements=list(elements)
    )


def _names(names: dict[str, str] | None) -> list[aas.LangStringNameType] | None:
    return [aas.LangStringNameType(lang, text) for lang, text in (names or {}).items()] or None
