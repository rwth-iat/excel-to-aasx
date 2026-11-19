"""Result of comparing a produced package against a reference package."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Difference:
    path: str
    field: str
    expected: str
    actual: str


@dataclass(frozen=True)
class Mount:
    submodel: str
    path: str  # "" means the submodel root

    def place(self, relative_path: str) -> str:
        return f"{self.path}/{relative_path}" if self.path else relative_path


@dataclass(frozen=True)
class ComparisonReport:
    mount: Mount
    elements_checked: int
    concepts_checked: int
    differences: tuple[Difference, ...]
