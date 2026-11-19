import base64

import pytest

from excel_to_aasx.domain.document.args import parse_args
from excel_to_aasx.domain.document.assets import (
    asset_name,
    blob_bytes,
    guess_extension,
    safe_file_name,
)
from excel_to_aasx.domain.document.nodes import asciidoc_function

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def test_parse_args_is_lenient_like_newtonsoft():
    args = parse_args('{ "noLink" : "true", "itemsA": ["a", "b",], "itemsC": ["c"], "depth": 2 }')
    assert args.no_link and args.depth == 2
    assert args.items == {"A": ("a", "b"), "C": ("c",)}
    assert parse_args("") == parse_args("   ")


def test_parse_args_rejects_garbage():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_args("{ nope")
    with pytest.raises(ValueError, match="JSON object"):
        parse_args("[1]")


def test_blob_bytes_decodes_base64_only_for_non_text_ascii():
    assert blob_bytes(base64.b64encode(PNG), "image/png") == PNG
    assert blob_bytes(PNG, "image/png") == PNG
    assert blob_bytes(b"a: b", "text/plain") == b"a: b"


def test_guess_extension():
    assert guess_extension(PNG) == ".png"
    assert guess_extension(b"GIF89a...") == ".gif"
    assert guess_extension(b"<svg") == ".png"


def test_asset_name():
    assert asset_name("my-theme_dot_yml", ".txt") == "my-theme.yml"
    assert asset_name("Logo", ".png") == "Logo.png"
    assert asset_name("a b", ".png") == "a_b.png"


@pytest.mark.parametrize(
    ("name", "safe"),
    [("x.ttf", "x.ttf"), ("../../etc/passwd", "passwd"), ("..\\a.rb", "a.rb"), ("..", "asset")],
)
def test_safe_file_name(name, safe):
    assert safe_file_name(name) == safe


def test_asciidoc_function():
    prefix = "http://admin-shell.io/aasx-package-explorer/functions/asciidoc/"
    assert asciidoc_function(prefix + "heading1/1/0") == "heading1"
    assert asciidoc_function(prefix + "heading1/2/0") == ""
    assert asciidoc_function("0173-1#02-AAO677") == ""
