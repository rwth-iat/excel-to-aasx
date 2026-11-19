import datetime

from excel_to_aasx.domain.document.nodes import SUBMODEL_SEMANTIC_ID
from excel_to_aasx.domain.document.starter import starter_nodes
from excel_to_aasx.ports.package_editor import FrameSource, PackageEditor


def add_document(
    editor: PackageEditor,
    frames: FrameSource,
    source: str,
    target: str,
    submodel: str | None,
    today: datetime.date,
    template: str = "idta",
) -> str:
    """Add an IDTA starter document for the data submodel (ADR 0008). Returns its idShort.

    `submodel` is the idShort of the data submodel; needed only if the package has several.
    """
    models = editor.models(source)
    if any(_is_document(m.semantic_id) for m in models.values()):
        raise ValueError("the package already has an AsciiDoc document submodel")
    candidates = {sid: m for sid, m in models.items() if submodel in (None, m.id_short)}
    if len(candidates) != 1:
        names = ", ".join(sorted(m.id_short for m in models.values())) or "none"
        raise ValueError(f"choose the data submodel with --submodel (found: {names})")
    data_id, data = next(iter(candidates.items()))
    nodes = starter_nodes(data, data_id, frames(template), today)
    return editor.add_document(source, target, nodes, data_id)


def _is_document(semantic_id) -> bool:
    return semantic_id is not None and any(v == SUBMODEL_SEMANTIC_ID for _, v in semantic_id.keys)
