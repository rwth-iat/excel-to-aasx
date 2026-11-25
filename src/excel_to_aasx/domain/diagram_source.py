"""What the live preview may send to PlantUML (ADR 0011): exactly one UML diagram.

PlantUML's `-pipe` renders every @start…@end pair in its input, and @start may name any of
its parsers (ditaa, gantt, latex, json, …). One request must cost one UML render, so the
text is reduced to a single @startuml block before it leaves the app.
"""

import re

_START_OR_END = re.compile(r"^\s*@(start|end)\w*", re.MULTILINE)
_NEWPAGE = re.compile(r"^\s*newpage\b", re.MULTILINE)


def single_uml_diagram(source: str) -> str:
    """The source as one @startuml…@enduml document. Raises `ValueError` otherwise.

    A block without @startuml/@enduml gets them, as asciidoctor-diagram does.
    """
    text = source.strip()
    if not text.startswith("@start"):
        text = f"@startuml\n{text}\n@enduml"
    markers = [m.group(0).strip() for m in _START_OR_END.finditer(text)]
    if len(markers) != 2 or not markers[0].startswith("@startuml"):
        raise ValueError("the preview renders one @startuml … @enduml diagram per block")
    if markers[1] != "@enduml" or not text.endswith("@enduml"):
        raise ValueError("the diagram must end with @enduml")
    if _NEWPAGE.search(text):
        raise ValueError("the preview does not render multi-page diagrams (newpage)")
    return text + "\n"


class RendererBusy(ValueError):
    """All render slots are taken; the caller may try again shortly."""
