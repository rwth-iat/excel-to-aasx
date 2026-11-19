"""`ExportSmt.Args` extension values: JSON, read as leniently as Newtonsoft.Json does."""

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExportArgs:
    no_link: bool = False
    file_name: str = ""
    depth: int | None = None
    width: float | None = None
    no_description: bool = False
    column_widths: tuple[float, ...] | None = None
    # itemsA, itemsB, ... for iterate-list, keyed by letter. The example PDF uses itemsC,
    # which the ported Package Explorer commit does not know yet; any letter is accepted.
    items: dict[str, tuple[str, ...]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def parse_args(text: str) -> ExportArgs:
    """Raises `ValueError` for JSON that even a lenient reading cannot parse."""
    if not text.strip():
        return ExportArgs()
    # The example has trailing commas, which Newtonsoft accepts and `json` does not.
    cleaned = re.sub(r",(\s*[\]}])", r"\1", text)
    try:
        raw = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(f"ExportSmt.Args is not valid JSON: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError("ExportSmt.Args must be a JSON object")
    return ExportArgs(
        no_link=_bool(raw.get("noLink")),
        file_name=str(raw.get("fileName") or ""),
        depth=int(raw["depth"]) if raw.get("depth") is not None else None,
        width=float(raw["width"]) if raw.get("width") is not None else None,
        no_description=_bool(raw.get("noDescription")),
        column_widths=tuple(float(w) for w in raw["columnWidths"])
        if raw.get("columnWidths")
        else None,
        items={
            key[-1]: tuple(str(x) for x in value or ())
            for key, value in raw.items()
            if re.fullmatch(r"items[A-Z]", key)
        },
        raw=raw,
    )


def _bool(value: object) -> bool:
    # Newtonsoft turns the string "true" into a bool; the example writes it that way.
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def link_attributes(args: ExportArgs, title: str) -> str:
    """EvalLinkArguments."""
    text = ""
    if args.width is not None:
        text += f',width="{args.width:.1f}%"'
    if title:
        text += ',title="{}"'.format(title.replace('"', '\\"'))
    return text.strip(",")
