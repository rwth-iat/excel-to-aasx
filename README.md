# excel-to-aasx

Converts vendor Excel property sheets (NAMUR SMT import format) into AASX packages
(AAS metamodel V3.1), matching the "Import NAMUR SMTs" table import of the
[AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer).

Planned: AASX to AsciiDoc rendering, and a web editor with live PDF preview.

## Setup

```bash
uv sync
uv run excel-to-aasx import examples/Import_Properties_Schwebe_2_added_Li_v09_HOMI_Gerd-1.xlsx -o out/import.aasx
uv run excel-to-aasx diff out/import.aasx "examples/Namur_SMT_VariableAreaFlowMeters_v09_2nd_delivery (1).aasx"
uv run excel-to-aasx add-document out/import.aasx -o out/with-doc.aasx   # IDTA starter document
uv run excel-to-aasx adoc "examples/Namur_SMT_VariableAreaFlowMeters_v09_2nd_delivery (1).aasx" -o out/doc
uv run excel-to-aasx pdf "examples/Namur_SMT_VariableAreaFlowMeters_v09_2nd_delivery (1).aasx" -o out/pdf
```

`pdf` needs Docker and the image `asciidoctor/docker-asciidoctor:1.108.1`
(`docker pull asciidoctor/docker-asciidoctor:1.108.1`). The build runs in a locked-down
container in secure mode; see `docs/decisions/0004-pdf-build-in-locked-down-docker.md`.

`import` exits 1 when rows were skipped because of errors (the AASX is still written), 2 when the
workbook cannot be read. `diff` exits 1 when differences were found.

## Docs

- Import rules: [`docs/spec/namur-import.md`](docs/spec/namur-import.md)
- AsciiDoc export rules: [`docs/spec/asciidoc-export.md`](docs/spec/asciidoc-export.md)
- Decisions: [`docs/decisions/`](docs/decisions/)
