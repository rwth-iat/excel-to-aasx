"""What the comparison sees of an AAS package: element facts by path, concepts by id."""

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ElementFacts:
    kind: str
    semantic_id: str = ""
    cardinality: str = ""
    value_type: str = ""


@dataclass(frozen=True)
class ConceptFacts:
    id_short: str = ""
    preferred_names: tuple[tuple[str, str], ...] = ()
    unit: str = ""


@dataclass(frozen=True)
class PackageSnapshot:
    """`submodels` maps a submodel idShort to its elements, keyed by path ("A/B/C")."""

    submodels: Mapping[str, Mapping[str, ElementFacts]] = field(default_factory=dict)
    concepts: Mapping[str, ConceptFacts] = field(default_factory=dict)
