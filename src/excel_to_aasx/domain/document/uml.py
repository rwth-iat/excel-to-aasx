"""PlantUML class diagram of a submodel part (Package Explorer Uml/PlantUmlWriter + BaseWriter)."""

from dataclasses import dataclass
from typing import Any

from excel_to_aasx.domain.document.tables.model import Element
from excel_to_aasx.domain.document.tables.placeholders import ABBREVIATIONS

UML_CLASS_KINDS = frozenset(
    {"Submodel", "SubmodelElementCollection", "SubmodelElementList", "Entity", "Operation"}
)
_CARDINALITY = {"ZeroToOne": "0..1", "ZeroToMany": "0..*", "OneToMany": "1..*"}
_DROPINS = (
    ("https://admin-shell.io/smt-dropin/smt-dropin-definition/1/0", "smt-dropin-definition"),
    ("https://admin-shell.io/smt-dropin/smt-dropin-use/1/0", "smt-dropin-use"),
)


@dataclass(frozen=True)
class UmlOptions:
    """ExportUmlRecord; read from the `uml` object of ExportSmt.Args."""

    suppress: tuple[str, ...] = ()
    limit_initial_value: int = 15
    outline: bool = False
    swap_direction: bool = False
    classes_from_concepts: bool = False
    no_association_names: bool = False

    @classmethod
    def from_args(cls, raw: Any) -> "UmlOptions":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            suppress=tuple(str(raw.get("Suppress") or "").split()),
            limit_initial_value=int(raw.get("LimitInitialValue", 15)),
            outline=bool(raw.get("Outline", False)),
            swap_direction=bool(raw.get("SwapDirection", False)),
            classes_from_concepts=bool(raw.get("ClassesFromConcepts", False)),
            no_association_names=bool(raw.get("NoAssociationNames", False)),
        )


def plantuml(top: Element, depth: int, options: UmlOptions) -> str:
    return _Writer(options).document(top, depth)


class _Writer:
    def __init__(self, options: UmlOptions) -> None:
        self._options = options
        self._lines: list[str] = []
        self._post: list[str] = []
        self._next_id = 0
        self._next_unnamed = 1

    def document(self, top: Element, depth: int) -> str:
        direction = (
            "top to bottom direction" if self._options.swap_direction else "left to right direction"
        )
        self._lines += [
            "@startuml", "!theme plain", direction, "hide class circle", "hide class methods",
            "skinparam classAttributeIconSize 0", "' skinparam linetype polyline",
            "skinparam linetype ortho", "",
        ]  # fmt: skip
        info = f" {top.id_short}"
        if top.kind == "Submodel" and top.submodel_kind:
            info = ("SMT" if top.submodel_kind == "Template" else "SM") + info
        self._lines += [f"mainframe {info}", ""]
        self._entity(None, top, top.id_short, depth)
        return "\n".join([*self._lines, *self._post, "@enduml"]) + "\n"

    def _entity(self, parent: Element | None, rf: Element, visible: str, remain: int) -> str | None:
        class_id = self._class(rf, visible)
        if remain > 1:
            for index, child in enumerate(rf.children):
                child_name = _visible(rf, index, child)
                child_id = self._entity(rf, child, child_name, remain - 1)
                if child_id and class_id:
                    multiplicity = _multiplicity(child)
                    multiplicity = f'"{multiplicity}"' if multiplicity else ""
                    name = self._clear(child_name)
                    if self._options.outline or self._options.no_association_names:
                        multiplicity, name = "", ""
                    self._post.append(f'{class_id} *-- {multiplicity} {child_id} : "{name}"')
        return class_id

    def _class(self, rf: Element, visible: str) -> str | None:
        if rf.kind not in UML_CLASS_KINDS or self._suppressed(rf.id_short):
            return None
        self._next_id += 1
        class_id = f"ID{self._next_id:08X}"
        concept_name = self._concept_class_name(rf)
        if concept_name:
            visible = concept_name
        stereotype = f"<<{_feature_type(rf, None)}>>"
        supplemental = {ref.text(2) for ref in rf.supplemental_ids}
        stereotype += "".join(f" <<{label}>>" for key, label in _DROPINS if key in supplemental)
        self._lines.append(f'class "{self._clear(visible)}" as {class_id} {stereotype} {{')
        if not self._options.outline:
            for index, feature in enumerate(rf.children):
                self._lines.append(self._feature_line(rf, index, feature))
        self._lines += ["}", ""]
        return class_id

    def _feature_line(self, rf: Element, index: int, feature: Element) -> str:
        line = f"  +{_visible(rf, index, feature)}"
        if feature_type := _feature_type(feature, self._concept_class_name(feature)):
            line += f" : {feature_type}"
        if multiplicity := _multiplicity(feature):
            line += f" [{multiplicity}]"
        if initial := self._initial_value(feature):
            line += f' = "{initial}"'
        return line

    def _initial_value(self, element: Element) -> str:
        limit = self._options.limit_initial_value
        if limit == 0 or element.kind not in ("Property", "Range", "MultiLanguageProperty"):
            return ""
        text = element.value_text
        if limit != -1 and len(text) > limit:
            text = text[: max(0, limit - 3)] + "..."
        return text

    def _concept_class_name(self, rf: Element) -> str | None:
        """EvalPossibleConceptClassName: the CD idShort, when ClassesFromConcepts is set."""
        concept = rf.concept
        if (
            not self._options.classes_from_concepts
            or rf.kind not in UML_CLASS_KINDS
            or concept is None
        ):
            return None
        if concept.id_short.strip() and concept.id_short.strip() != rf.id_short.strip():
            return concept.id_short
        return None

    def _suppressed(self, id_short: str) -> bool:
        return any(word.lower() in id_short.lower() for word in self._options.suppress)

    def _clear(self, name: str) -> str:
        name = name.replace('"', "")
        if not name.strip():
            name = f"NN{self._next_unnamed:03d}"
            self._next_unnamed += 1
        return name


def _visible(parent: Element, index: int, rf: Element) -> str:
    """ViusalIdShort: list items are shown with their position."""
    return f"[{index:02d}] {rf.id_short}" if parent.kind == "SubmodelElementList" else rf.id_short


def _feature_type(rf: Element, concept_name: str | None) -> str:
    if rf.kind == "Property":
        return rf.value_type
    return concept_name or ABBREVIATIONS.get(rf.kind, "")


def _multiplicity(rf: Element) -> str:
    """EvalUmlMultiplicity with noOne: cardinality One gives no text."""
    value = next((v for t, v in rf.qualifiers if t == "SMT/Cardinality"), None)
    return _CARDINALITY.get(value or "", "")
