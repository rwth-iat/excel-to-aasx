"""Superset comparison of two package snapshots (ADR 0003).

Every element and concept in `expected` must exist in `reference` with the same facts.
Anything extra in `reference` is allowed.
"""

import re
from collections.abc import Iterable, Mapping

from excel_to_aasx.domain.report import ComparisonReport, Difference, Mount
from excel_to_aasx.domain.snapshot import ConceptFacts, ElementFacts, PackageSnapshot

_VERSION_SUFFIX = re.compile(r"#\d{3}$")


def strip_version(identifier: str) -> str:
    """ECLASS IRDIs carry a `#NNN` version; reference packages often use a newer one."""
    return "/".join(_VERSION_SUFFIX.sub("", part) for part in identifier.split("/"))


def find_mount(
    expected: Mapping[str, ElementFacts], reference: Mapping[str, Mapping[str, ElementFacts]]
) -> Mount | None:
    """The submodel and container path in `reference` where most of `expected` lines up."""
    best: tuple[int, Mount] | None = None
    for submodel, elements in reference.items():
        for mount_path in ["", *elements]:
            mount = Mount(submodel, mount_path)
            hits = sum(1 for path in expected if mount.place(path) in elements)
            if hits and (best is None or hits > best[0]):
                best = (hits, mount)
    return best[1] if best else None


def compare_elements(
    expected: Mapping[str, ElementFacts], reference: Mapping[str, ElementFacts], mount: Mount
) -> list[Difference]:
    differences = []
    for path, facts in expected.items():
        actual = reference.get(mount.place(path))
        if actual is None:
            differences.append(Difference(path, "missing", facts.kind, ""))
            continue
        differences.extend(
            Difference(path, name, want, got)
            for name, want, got in _element_fields(facts, actual)
            if want != got
        )
    return differences


def _element_fields(want: ElementFacts, got: ElementFacts) -> list[tuple[str, str, str]]:
    return [
        ("kind", want.kind, got.kind),
        ("semantic_id", strip_version(want.semantic_id), strip_version(got.semantic_id)),
        ("cardinality", want.cardinality, got.cardinality),
        ("value_type", want.value_type, got.value_type),
        ("display_names", _langs(sorted(want.display_names)), _langs(sorted(got.display_names))),
    ]


def compare_concepts(
    expected: Mapping[str, ConceptFacts], reference: Mapping[str, ConceptFacts]
) -> list[Difference]:
    by_unversioned = {strip_version(cd_id): facts for cd_id, facts in reference.items()}
    differences = []
    for cd_id, facts in expected.items():
        actual = by_unversioned.get(strip_version(cd_id))
        if actual is None:
            differences.append(Difference(cd_id, "concept missing", facts.id_short, ""))
            continue
        for name in ("id_short", "unit"):
            want, got = getattr(facts, name), getattr(actual, name)
            if want != got:
                differences.append(Difference(cd_id, f"concept {name}", want, got))
        for name in ("preferred_names", "definitions"):
            want, got = getattr(facts, name), getattr(actual, name)
            if set(want) - set(got):
                differences.append(Difference(cd_id, f"concept {name}", _langs(want), _langs(got)))
    return differences


def compare_snapshots(
    expected: PackageSnapshot, reference: PackageSnapshot, mount: Mount
) -> ComparisonReport:
    expected_elements = _single_submodel(expected)
    differences = [
        *compare_elements(expected_elements, reference.submodels.get(mount.submodel, {}), mount),
        *compare_concepts(expected.concepts, reference.concepts),
    ]
    return ComparisonReport(
        mount, len(expected_elements), len(expected.concepts), tuple(differences)
    )


def _single_submodel(snapshot: PackageSnapshot) -> Mapping[str, ElementFacts]:
    if len(snapshot.submodels) != 1:
        raise ValueError(
            f"expected package must hold exactly one submodel, found {len(snapshot.submodels)}"
        )
    return next(iter(snapshot.submodels.values()))


def _langs(names: Iterable[tuple[str, str]]) -> str:
    return "; ".join(f"{lang}: {text}" for lang, text in names)
