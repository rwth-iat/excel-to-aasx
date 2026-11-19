"""The target submodel as the table generator sees it."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

LangText = tuple[str, str]  # (language, text)
Key = tuple[str, str]  # (key type, value)


@dataclass(frozen=True)
class Ref:
    keys: tuple[Key, ...]

    def text(self, fmt: int = 1, delimiter: str = ",") -> str:
        """ExtendReference.ToStringExtended: fmt 1 `[Type, value]`, fmt 2 the bare values."""
        return delimiter.join(
            value if fmt == 2 else f"[{kind}, {value}]" for kind, value in self.keys
        )


@dataclass(frozen=True)
class Concept:
    id: str = ""
    id_short: str = ""
    preferred_names: tuple[LangText, ...] = ()
    definitions: tuple[LangText, ...] = ()
    unit: str = ""
    value_list: tuple[tuple[str, Ref | None], ...] | None = None
    is_case_of: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Element:
    kind: str  # "Submodel" or the AAS type name of a SubmodelElement
    id_short: str = ""
    description: tuple[LangText, ...] = ()
    semantic_id: Ref | None = None
    supplemental_ids: tuple[Ref, ...] = ()
    qualifiers: tuple[tuple[str, str], ...] = ()  # (type, value)
    value_text: str = ""  # ValueAsText
    value_type: str = ""  # Property only, e.g. "xs:string"
    value_id: Ref | None = None
    details: tuple[str, ...] = ()  # SML attributes as `name=value`
    concept: Concept | None = None
    submodel_kind: str = ""  # "Template" or "Instance"; submodels only
    children: tuple["Element", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Located:
    """An element with its parent, as FindReferableByReference returns it."""

    element: Element
    parent: Element | None


def resolve(models: Mapping[str, Element], keys: Sequence[str]) -> Located | None:
    """Follow reference keys: submodel id, then idShorts (or indexes inside lists)."""
    if not keys or keys[0] not in models:
        return None
    current, parent = models[keys[0]], None
    for key in keys[1:]:
        child = _child(current, key)
        if child is None:
            return None
        current, parent = child, current
    return Located(current, parent)


def _child(element: Element, key: str) -> Element | None:
    if element.kind == "SubmodelElementList" and key.isdigit():
        index = int(key)
        return element.children[index] if index < len(element.children) else None
    return next((c for c in element.children if c.id_short == key), None)
