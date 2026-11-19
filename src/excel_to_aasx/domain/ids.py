"""Identifier matching as the Package Explorer does it (MatchMode.IdNoVersion)."""

import re


def remove_version(identifier: str) -> str:
    """IriIrdiRemoveVersion, reproduced as is: Package Explorer matches CDs with it.

    `0173-1#02-AAO677#004` -> `0173-1#02-AAO677`. An `http:` IRI is cut at its first
    numeric path segment (`http://x/aas/1/0` -> `http://x/aas`); `https:` is left alone.
    """
    if re.match(r"^((\d{4,4}).*/)", identifier):
        parts = []
        for part in identifier.split("/"):
            found = re.search(r"((\d{4,4}).*)(#\d{2,4})", part)
            parts.append(found.group(1) if found else part)
        return "/".join(parts)
    if found := re.search(r"((\d{4,4}).*([A-Za-z0-9]{4,6}))(#\d{2,4})", identifier):
        identifier = found.group(1)
    if found := re.search(r"((http:).*?)(/\d{1,4}){1,2}", identifier):
        identifier = found.group(1)
    return identifier
