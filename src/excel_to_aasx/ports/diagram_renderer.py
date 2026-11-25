from typing import Protocol


class DiagramRenderer(Protocol):
    def render_svg(self, document: str) -> bytes:
        """Render one checked @startuml…@enduml document to SVG (ADR 0011).

        Raises `ValueError` when no SVG could be made. A syntax error is not a failure:
        PlantUML draws it into the SVG.
        """
        ...
