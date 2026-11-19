"""Files the document needs next to it: images, themes, scripts (ExportSmt.ProcessImageLink)."""

import base64
import binascii

_TEXT_TYPES = (
    "text/plain", "text/xml", "text/html", "text/markdown", "text/asciidoc",
    "application/json", "application/rdf+xml",
)  # fmt: skip
_SIGNATURES = (
    (".jpg", (b"\xff\xd8\xff\xdb", b"\xff\xd8\xff\xee", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")),
    (".gif", (b"GIF87a", b"GIF89a")),
    (".png", (b"\x89PNG\r\n\x1a\n",)),
)


def is_text_content_type(content_type: str) -> bool:
    lowered = content_type.strip().lower()
    return any(text_type in lowered for text_type in _TEXT_TYPES)


def blob_bytes(value: bytes, content_type: str) -> bytes:
    """PE stores binary blobs either raw or as base64 text; ASCII-only non-text means base64."""
    if is_text_content_type(content_type) or any(b >= 128 for b in value):
        return value
    try:
        return base64.b64decode(value, validate=False)
    except (binascii.Error, ValueError):
        return value


def blob_value(data: bytes, content_type: str) -> bytes:
    """Inverse of `blob_bytes`: what to store so Package Explorer reads `data` back."""
    if is_text_content_type(content_type) or any(b >= 128 for b in data):
        return data
    return base64.b64encode(data)


def guess_extension(data: bytes) -> str:
    for extension, signatures in _SIGNATURES:
        if any(data.startswith(signature) for signature in signatures):
            return extension
    return ".png"  # PE's fallback
