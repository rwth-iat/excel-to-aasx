from excel_to_aasx.domain.importing.blocks import find_blocks
from excel_to_aasx.domain.importing.build import build_submodel, generated_id
from excel_to_aasx.domain.importing.model import SubmodelDraft
from excel_to_aasx.domain.importing.result import ImportResult
from excel_to_aasx.ports.package_writer import PackageWriter
from excel_to_aasx.ports.sheet_reader import SheetReader

SUBMODEL_ID_TEMPLATE = "www.example.com/ids/sm/DDDD_DDDD_DDDD_DDDD"


def import_workbook(
    reader: SheetReader,
    writer: PackageWriter,
    source: str,
    target: str,
    submodel_id: str | None = None,
) -> ImportResult:
    """Excel workbook -> AASX package. Rows with errors are skipped and reported.

    Without `submodel_id`, the id is derived from the submodel's semanticId and idShort,
    so importing the same workbook twice gives the same id.
    """
    blocks = [
        block for sheet in reader.read(source) for block in find_blocks(sheet.name, sheet.rows)
    ]
    if not blocks:
        raise ValueError(f"{source}: no import block found (expected 'idShort:' in column A)")
    result = build_submodel(blocks, SubmodelDraft(id=submodel_id or "", id_short=""))
    if not submodel_id:
        submodel = result.submodel
        submodel.id = generated_id(
            SUBMODEL_ID_TEMPLATE, f"{submodel.semantic_id}/{submodel.id_short}"
        )
    result.issues.extend(writer.write(target, result))
    return result
