"""Open an AASX (OPC) package and load its AAS environment.

AASX files are untrusted ZIPs: members are only read by name, never extracted, and every
read is capped in size. XML goes through defusedxml.
"""

import posixpath
import zipfile
from xml.etree.ElementTree import Element

import aas_core3_1.types as aas
import aas_core3_1.xmlization as aas_xml
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring, iterparse

_RELS_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_ORIGIN_TYPES = {
    "http://admin-shell.io/aasx/relationships/aasx-origin",
    "http://www.admin-shell.io/aasx/relationships/aasx-origin",
}
_SPEC_TYPES = {
    "http://admin-shell.io/aasx/relationships/aas-spec",
    "http://www.admin-shell.io/aasx/relationships/aas-spec",
}


def load_environment(path: str, max_part_bytes: int) -> aas.Environment:
    try:
        with zipfile.ZipFile(path) as package:
            spec_part = _find_spec_part(package, max_part_bytes)
            if not spec_part.endswith(".xml"):
                raise ValueError(f"only XML AAS specs are supported, got {spec_part}")
            with package.open(_member(package, spec_part, max_part_bytes)) as stream:
                return aas_xml.environment_from_iterparse(
                    iterparse(stream, events=["start", "end"])
                )
    except zipfile.BadZipFile as error:
        raise ValueError(f"{path}: not a ZIP/AASX package") from error
    except DefusedXmlException as error:
        raise ValueError(f"{path}: forbidden XML construct ({error})") from error
    except OSError as error:
        raise ValueError(f"{path}: {error.strerror or error}") from error
    except aas_xml.DeserializationException as error:
        raise ValueError(f"{path}: invalid AAS XML at {error.path}: {error.cause}") from error


def _find_spec_part(package: zipfile.ZipFile, max_part_bytes: int) -> str:
    origin = _targets(package, "_rels/.rels", _ORIGIN_TYPES, max_part_bytes)
    if not origin:
        raise ValueError("no aasx-origin relationship in _rels/.rels")
    origin_part = origin[0]
    origin_dir, origin_name = posixpath.split(origin_part)
    rels_part = posixpath.join(origin_dir, "_rels", f"{origin_name}.rels")
    specs = _targets(package, rels_part, _SPEC_TYPES, max_part_bytes)
    if not specs:
        raise ValueError(f"no aas-spec relationship in {rels_part}")
    return specs[0]


def _targets(
    package: zipfile.ZipFile, rels_part: str, types: set[str], max_part_bytes: int
) -> list[str]:
    root: Element = fromstring(package.read(_member(package, rels_part, max_part_bytes)))
    return [
        posixpath.normpath(rel.get("Target", "")).lstrip("/")
        for rel in root.iter(f"{_RELS_NS}Relationship")
        if rel.get("Type") in types
    ]


def _member(package: zipfile.ZipFile, part: str, max_part_bytes: int) -> zipfile.ZipInfo:
    try:
        info = package.getinfo(part.lstrip("/"))
    except KeyError as error:
        raise ValueError(f"package part missing: {part}") from error
    if info.file_size > max_part_bytes:
        raise ValueError(f"package part {part} is {info.file_size} bytes, limit {max_part_bytes}")
    return info
