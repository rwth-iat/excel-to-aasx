"""Write an import result as an AASX (OPC) package with an XML AAS spec part."""

import re
import zipfile

import aas_core3_1.types as aas
import aas_core3_1.verification as aas_verification
import aas_core3_1.xmlization as aas_xml

from excel_to_aasx.adapters.aasx.environment import environment_of
from excel_to_aasx.domain.importing.result import ImportResult, Issue

_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_ORIGIN_TYPE = "http://admin-shell.io/aasx/relationships/aasx-origin"
_SPEC_TYPE = "http://admin-shell.io/aasx/relationships/aas-spec"
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="text/xml"/>'
    '<Override PartName="/aasx/aasx-origin" ContentType="text/plain"/>'
    "</Types>"
)


class AasxPackageWriter:
    def write(self, target: str, result: ImportResult) -> list[Issue]:
        environment = environment_of(result)
        spec_part = _spec_part_name(result.submodel.id_short)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr("[Content_Types].xml", _CONTENT_TYPES)
            package.writestr("_rels/.rels", _rels(_ORIGIN_TYPE, "/aasx/aasx-origin"))
            package.writestr("aasx/aasx-origin", "Intentionally empty.")
            package.writestr("aasx/_rels/aasx-origin.rels", _rels(_SPEC_TYPE, f"/{spec_part}"))
            package.writestr(spec_part, _xml(environment))
        # The import already reports invalid idShorts by element path, which reads better.
        return [
            Issue("warning", str(error.path), f"metamodel: {error.cause}")
            for error in aas_verification.verify(environment)
            if not str(error.path).endswith(".id_short")
        ]


def _spec_part_name(id_short: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]", "_", id_short) or "submodel"
    return f"aasx/{name}/{name}.aas.xml"


def _rels(rel_type: str, target: str) -> str:
    return (
        f'<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="{_RELS_NS}">'
        f'<Relationship Type="{rel_type}" Target="{target}" Id="R1"/></Relationships>'
    )


def _xml(environment: aas.Environment) -> str:
    return '<?xml version="1.0" encoding="utf-8"?>' + aas_xml.to_str(environment)
