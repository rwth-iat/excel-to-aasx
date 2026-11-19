import pytest

from excel_to_aasx.domain.compare import (
    compare_concepts,
    compare_elements,
    compare_snapshots,
    find_mount,
    strip_version,
)
from excel_to_aasx.domain.report import Difference, Mount
from excel_to_aasx.domain.snapshot import ConceptFacts, ElementFacts, PackageSnapshot

PROP = ElementFacts("Property", "0173-1#02-AAO676#005", "One", "xs:string")
SMC = ElementFacts("SubmodelElementCollection", "0173-1#02-temp1", "One")


def test_strip_version_removes_suffix_in_every_part():
    assert strip_version("0173-1#02-ABK161#002/0173-1#01-AHX838#002") == (
        "0173-1#02-ABK161/0173-1#01-AHX838"
    )
    assert strip_version("https://example.com/x#001") == "https://example.com/x"
    assert strip_version("0173-1#02-AAO676") == "0173-1#02-AAO676"


def test_find_mount_prefers_container_with_most_matches():
    expected = {"General": SMC, "General/Number": PROP}
    reference = {
        "Other": {"General": SMC},
        "Data": {
            "Areas": SMC,
            "Areas/V17": SMC,
            "Areas/V17/General": SMC,
            "Areas/V17/General/Number": PROP,
        },
    }
    assert find_mount(expected, reference) == Mount("Data", "Areas/V17")


def test_find_mount_none_without_overlap():
    assert find_mount({"A": SMC}, {"S": {"B": SMC}}) is None


def test_compare_elements_ignores_versions_and_extras():
    reference = {"M/General": SMC, "M/General/Number": PROP, "M/General/Extra": PROP}
    unversioned = ElementFacts("Property", "0173-1#02-AAO676", "One", "xs:string")
    assert (
        compare_elements(
            {"General": SMC, "General/Number": unversioned}, reference, Mount("S", "M")
        )
        == []
    )


def test_compare_elements_reports_missing_and_changed_fields():
    reference = {
        "General": SMC,
        "General/Number": ElementFacts("MultiLanguageProperty", "x", "ZeroToOne"),
    }
    expected = {"General/Number": PROP, "General/Gone": PROP}
    assert compare_elements(expected, reference, Mount("S", "")) == [
        Difference("General/Number", "kind", "Property", "MultiLanguageProperty"),
        Difference("General/Number", "semantic_id", "0173-1#02-AAO676", "x"),
        Difference("General/Number", "cardinality", "One", "ZeroToOne"),
        Difference("General/Number", "value_type", "xs:string", ""),
        Difference("General/Gone", "missing", "Property", ""),
    ]


def test_compare_concepts_matches_unversioned_ids_and_allows_extra_languages():
    expected = {"0173-1#02-AAO676": ConceptFacts("Number", (("en", "number"),), "")}
    reference = {
        "0173-1#02-AAO676#005": ConceptFacts("Number", (("en", "number"), ("de", "Nummer")), "")
    }
    assert compare_concepts(expected, reference) == []


def test_compare_concepts_reports_differences():
    expected = {"a": ConceptFacts("A", (("en", "a"),), "mm"), "b": ConceptFacts("B")}
    reference = {"a": ConceptFacts("A2", (("en", "other"),), "m")}
    fields = [d.field for d in compare_concepts(expected, reference)]
    assert fields == [
        "concept id_short",
        "concept unit",
        "concept preferred_names",
        "concept missing",
    ]


def test_compare_snapshots_needs_exactly_one_expected_submodel():
    two = PackageSnapshot(submodels={"A": {}, "B": {}})
    with pytest.raises(ValueError, match="exactly one submodel"):
        compare_snapshots(two, PackageSnapshot(), Mount("A", ""))
