"""The submodel as the import builds it, before it becomes AAS objects."""

from dataclasses import dataclass, field

LangText = tuple[str, str]  # (language, text)

CONTAINER_KINDS = frozenset({"SubmodelElementCollection", "SubmodelElementList"})


@dataclass(frozen=True)
class Sheet:
    name: str
    rows: list[list[str]]


@dataclass
class Element:
    kind: str
    id_short: str
    semantic_id: str = ""
    display_names: list[LangText] = field(default_factory=list)
    description: list[LangText] = field(default_factory=list)
    cardinality: str = ""
    value_type: str = ""
    children: list["Element"] = field(default_factory=list)

    @property
    def is_container(self) -> bool:
        return self.kind in CONTAINER_KINDS


@dataclass(frozen=True)
class Concept:
    id: str
    id_short: str
    preferred_names: tuple[LangText, ...] = ()
    definitions: tuple[LangText, ...] = ()
    unit: str = ""


@dataclass
class SubmodelDraft:
    id: str
    id_short: str
    semantic_id: str = ""
    description: list[LangText] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
