"""A package opened for editing: where it is and what the export produced."""

from dataclasses import dataclass, field

from excel_to_aasx.domain.document.render import RenderedDocument
from excel_to_aasx.domain.importing.result import Issue


@dataclass
class OpenedDocument:
    package: str  # AASX with data and document submodel
    main_file: str  # the exported .adoc
    document: RenderedDocument
    issues: list[Issue] = field(default_factory=list)
