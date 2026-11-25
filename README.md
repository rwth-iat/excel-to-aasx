# excel-to-aasx

Converts vendor Excel property sheets (NAMUR SMT import format) into AASX packages
(AAS metamodel V3.1), matching the "Import NAMUR SMTs" table import of the
[AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer).

It also renders a submodel as an IDTA-style AsciiDoc specification and builds the PDF,
from the command line or in a browser editor with a live preview.

## Setup

```bash
uv sync
uv run excel-to-aasx import src/excel_to_aasx/adapters/web/static/examples/demo-level-sensor.xlsx -o out/import.aasx
uv run excel-to-aasx add-document out/import.aasx -o out/with-doc.aasx   # IDTA starter document
uv run excel-to-aasx adoc out/with-doc.aasx -o out/doc
uv run excel-to-aasx pdf out/with-doc.aasx -o out/pdf
uv run excel-to-aasx diff out/import.aasx reference.aasx                # superset check against a reference
```

The demo workbook has invented values (`tools/make_demo_workbook.py` writes it).

### Reference files

The project was built against a vendor workbook, AASX and PDF that may not be published, so they
are not in git ([ADR 0010](docs/decisions/0010-reference-files-stay-out-of-git.md)). If you have
them, put them in `examples/` (ignored by git) and compare by hand with `diff`. No test reads
them; the tests use the demo workbook.

## Web app

```bash
uv run excel-to-aasx serve --port 8000
```

Open http://127.0.0.1:8000, upload a workbook or an AASX, download the AASX, edit the AsciiDoc
with a live HTML preview and build the PDF on request. No workbook at hand? The home page offers
a demo workbook with invented values (`tools/make_demo_workbook.py` writes it): convert it with
one click, or download it to see the expected layout. Nothing is stored: sessions are
temporary folders (`EXCEL_TO_AASX_WORKSPACES`, default in the system temp dir) deleted after
two hours idle. Edits stay in the AsciiDoc download and the PDF; the AASX download contains the
starter document, not the edits.

To run the app with its PDF builder as containers: `docker compose up -d --build`
(see [`docs/deployment.md`](docs/deployment.md)).

`pdf` needs Docker and the image `asciidoctor/docker-asciidoctor:1.108.1`
(`docker pull asciidoctor/docker-asciidoctor:1.108.1`). The build runs in a locked-down
container in secure mode; see `docs/decisions/0004-pdf-build-in-locked-down-docker.md`.

`import` exits 1 when rows were skipped because of errors (the AASX is still written), 2 when the
workbook cannot be read. `diff` exits 1 when differences were found.

## Docs

- Import rules: [`docs/spec/namur-import.md`](docs/spec/namur-import.md)
- AsciiDoc export rules: [`docs/spec/asciidoc-export.md`](docs/spec/asciidoc-export.md)
- Deployment: [`docs/deployment.md`](docs/deployment.md)
- Decisions: [`docs/decisions/`](docs/decisions/)

## License

Apache License 2.0, see [`LICENSE`](LICENSE). Parts of the code are ports of the Eclipse AASX
Package Explorer (also Apache 2.0); [`NOTICE`](NOTICE) lists them and the third-party files.
The reference files in `examples/` are third-party material, not part of this repository.
