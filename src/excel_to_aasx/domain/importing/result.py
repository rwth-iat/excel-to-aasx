from dataclasses import dataclass, field

from excel_to_aasx.domain.importing.model import Concept, SubmodelDraft


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    location: str  # "Sheet!row" or a package path
    message: str


@dataclass
class ImportResult:
    submodel: SubmodelDraft
    concepts: list[Concept] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)
