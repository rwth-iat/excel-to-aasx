from excel_to_aasx.domain.document.tables.model import Concept, Element, Ref
from excel_to_aasx.domain.document.uml import UmlOptions, plantuml

ONE_OPTIONAL = (("SMT/Cardinality", "ZeroToOne"),)


def _tree() -> Element:
    image = Element("SubmodelElementCollection", "", children=(Element("File", "ImageFile"),))
    images = Element(
        "SubmodelElementList", "ProductImages", qualifiers=ONE_OPTIONAL, children=(image,)
    )
    return Element(
        "SubmodelElementCollection",
        "General",
        children=(
            Element("Property", "Name", value_type="xs:string", value_text="ACME"),
            images,
        ),
    )


def test_classes_features_and_associations():
    text = plantuml(_tree(), 5, UmlOptions())
    assert text.startswith("@startuml\n!theme plain\nleft to right direction\n")
    assert 'class "General" as ID00000001 <<SMC>> {\n  +Name : xs:string = "ACME"\n' in text
    assert "  +ProductImages : SML [0..1]\n}" in text
    assert 'class "[00] " as ID00000003 <<SMC>> {\n  +ImageFile : File\n}' in text
    assert 'ID00000002 *--  ID00000003 : "[00] "' in text
    assert 'ID00000001 *-- "0..1" ID00000002 : "ProductImages"' in text
    assert text.endswith("@enduml\n")


def test_options_limit_suppress_and_names():
    options = UmlOptions(
        limit_initial_value=0, suppress=("productimages",), no_association_names=True
    )
    text = plantuml(_tree(), 5, options)
    assert '= "ACME"' not in text
    assert 'class "ProductImages"' not in text
    assert 'class "[00] "' in text  # children of a suppressed class are still drawn, as in PE


def test_depth_one_draws_only_top():
    assert plantuml(_tree(), 1, UmlOptions()).count('class "') == 1


def test_submodel_mainframe_and_dropin_stereotype():
    dropin = Ref((("GlobalReference", "https://admin-shell.io/smt-dropin/smt-dropin-use/1/0"),))
    sm = Element("Submodel", "Data", submodel_kind="Template", supplemental_ids=(dropin,))
    text = plantuml(sm, 1, UmlOptions())
    assert "mainframe SMT Data\n" in text
    assert 'class "Data" as ID00000001 <<SM>> <<smt-dropin-use>> {' in text


def test_classes_from_concepts():
    smc = Element("SubmodelElementCollection", "X", concept=Concept(id_short="Concept"))
    text = plantuml(smc, 1, UmlOptions(classes_from_concepts=True))
    assert 'class "Concept" as ID00000001' in text


def test_options_from_args():
    options = UmlOptions.from_args(
        {"LimitInitialValue": 0, "NoAssociationNames": True, "Suppress": "a b"}
    )
    assert options == UmlOptions(
        suppress=("a", "b"), limit_initial_value=0, no_association_names=True
    )
    assert UmlOptions.from_args(None) == UmlOptions()
