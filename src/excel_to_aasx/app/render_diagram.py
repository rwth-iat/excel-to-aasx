"""PlantUML block of the live preview -> SVG (ADR 0011)."""

from excel_to_aasx.domain.diagram_source import single_uml_diagram
from excel_to_aasx.ports.diagram_renderer import DiagramRenderer


def render_diagram(renderer: DiagramRenderer, source: str) -> bytes:
    """Raises `ValueError` for text that is not one UML diagram, or when rendering fails."""
    return renderer.render_svg(single_uml_diagram(source))
